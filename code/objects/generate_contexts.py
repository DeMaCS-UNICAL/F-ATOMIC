"""
Query an LLM through Eden AI once per entity and save every response.

Eden AI exposes an OpenAI-compatible chat API, so the call uses the OpenAI SDK pointed at
the Eden AI base URL. The output cleaning is the one of UnifiedGenerator, without the
project-specific dependencies (settings, logger). The API key is read from the
EDENAI_API_KEY environment variable (or from the project .env file).

Input : CSV with an `entity` column (e.g. experiments/objects/results/entity_classification.csv)
Output: <out>.jsonl      one record per call: raw output, parsed contexts, problems,
                         model returned by the API, token usage, timestamp
        <out>.csv        one row per entity and context, list fields as JSON strings

The JSONL is also the checkpoint: re-running skips entities whose last record is ok.

Find the model id (format provider/model):
    python code/objects/generate_contexts.py --list-models deepseek

Example (pilot on the first 20 pending entities):
    python code/objects/generate_contexts.py --input experiments/objects/results/entity_classification.csv \
        --out experiments/objects/results/generated_contexts --model <id printed by --list-models> --limit 20
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import (APIConnectionError, APITimeoutError, AsyncOpenAI,
                    InternalServerError, OpenAI, RateLimitError)
from tenacity import (before_sleep_log, retry, retry_if_exception_type,
                      stop_after_attempt, wait_exponential)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))

from objects.prompts import (EXCLUDED_ENTITIES, RELATION_FIELDS, SYSTEM_PROMPT,
                                   build_messages, check_contexts, parse_output)

EDEN_BASE_URL = "https://api.edenai.run/v3/llm"
API_KEY_ENV = "EDENAI_API_KEY"
PROMPT_VERSION = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]
RETRYABLE = (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)

log = logging.getLogger("generate_contexts")

load_dotenv(ROOT / ".env")  # EDENAI_API_KEY is loaded from the repository root.

TEMPERATURE = 0.7
SEED = 42  # set to None if the provider rejects the `seed` parameter
MAX_TOKENS = 2048
CONCURRENCY = 5
MAX_ATTEMPTS = 5


def clean_json(text: str) -> str:
    """Strip chain-of-thought tags and markdown fences."""
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.replace("```json", "").replace("```", "").strip()


def make_caller(client, args):
    """Chat completion call with exponential backoff on rate limits and transient errors only."""
    @retry(
        retry=retry_if_exception_type(RETRYABLE),
        stop=stop_after_attempt(MAX_ATTEMPTS),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )
    async def call(messages):
        kwargs = dict(model=args.model, messages=messages,
                      temperature=TEMPERATURE, max_tokens=MAX_TOKENS)
        if SEED is not None:
            kwargs["seed"] = SEED
        return await client.chat.completions.create(**kwargs)
    return call


async def process_entity(entity, call, sem, args, out_f, stats):
    async with sem:
        record = {
            "entity": entity,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "base_url": EDEN_BASE_URL,
            "model_requested": args.model,
            "temperature": TEMPERATURE,
            "seed": SEED,
            "prompt_version": PROMPT_VERSION,
        }
        t0 = time.time()
        try:
            resp = await call(build_messages(entity))
        except Exception as e:  # non-retryable error or retries exhausted
            record.update(status="api_error", error=repr(e))
        else:
            choice = resp.choices[0]
            raw = choice.message.content or ""
            usage = getattr(resp, "usage", None)
            record.update(
                model_returned=getattr(resp, "model", None),
                finish_reason=choice.finish_reason,
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
                raw_output=raw,
            )
            try:
                ctxs = parse_output(clean_json(raw))
                record.update(status="ok",
                              contexts=[c.model_dump() for c in ctxs],
                              problems=check_contexts(ctxs, entity))
            except Exception as e:  # invalid JSON or wrong structure
                record.update(status="parse_error", error=repr(e))
        record["latency_s"] = round(time.time() - t0, 2)

        out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_f.flush()

        stats["calls"] += 1
        stats[record["status"]] += 1
        if record["status"] == "ok":
            stats["ok_empty_list" if not record["contexts"] else "ok_with_contexts"] += 1
            if record["problems"]:
                stats["ok_with_problems"] += 1
        if record.get("finish_reason") == "length":
            stats["truncated"] += 1
        if stats["calls"] % 10 == 0:
            log.info("completed %d calls", stats["calls"])


def last_records(jsonl: Path) -> dict:
    """Last record per entity (a re-run appends a new record for retried entities)."""
    last = {}
    if jsonl.exists():
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    last[r["entity"]] = r
    return last


def export_csv(jsonl: Path, csv_path: Path) -> int:
    rows = []
    for ent, r in last_records(jsonl).items():
        if r["status"] != "ok":
            continue
        for i, c in enumerate(r["contexts"]):
            row = {"entity": ent, "context_idx": i,
                   "crime_category": c["crime_category"],
                   "crime_subcategory": c["crime_subcategory"],
                   "brief_context": c["brief_context"]}
            for f in RELATION_FIELDS:
                row[f] = json.dumps(c[f], ensure_ascii=False)
            row["problems"] = json.dumps(r["problems"], ensure_ascii=False)
            rows.append(row)
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return len(rows)


async def run(entities, args, client):
    out = Path(args.out)
    jsonl = out.with_suffix(".jsonl")
    stats = Counter()
    sem = asyncio.Semaphore(CONCURRENCY)
    call = make_caller(client, args)
    with open(jsonl, "a", encoding="utf-8") as out_f:
        await asyncio.gather(*(process_entity(e, call, sem, args, out_f, stats)
                               for e in entities))
    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input")
    ap.add_argument("--out", help="output prefix, e.g. out/generated")
    ap.add_argument("--model", help="Eden AI model id, in the provider/model format")
    ap.add_argument("--limit", type=int, help="process at most N pending entities")
    ap.add_argument("--list-models", nargs="?", const="", metavar="FILTER",
                    help="print the available model ids (optionally filtered) and exit")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    api_key = os.environ.get(API_KEY_ENV)
    if not api_key:
        raise SystemExit(f"Set the {API_KEY_ENV} environment variable.")

    if args.list_models is not None:
        for m in OpenAI(base_url=EDEN_BASE_URL, api_key=api_key).models.list():
            if args.list_models.lower() in m.id.lower():
                print(m.id)
        return
    if not (args.input and args.out and args.model):
        raise SystemExit("--input, --out and --model are required.")

    df = pd.read_csv(args.input)
    df = df[df["physical"].isin(["yes", "maybe"])]
    entities = (df["entity"].dropna().astype(str).drop_duplicates().tolist())
    n_in_csv = len(entities)

    entities = [e for e in entities if e not in EXCLUDED_ENTITIES]
    n_excluded = n_in_csv - len(entities)

    jsonl = Path(args.out).with_suffix(".jsonl")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    done = {e for e, r in last_records(jsonl).items() if r["status"] == "ok"}
    pending = [e for e in entities if e not in done]
    n_pending_total = len(pending)
    if args.limit:
        pending = pending[:args.limit]
    log.info("entities: %d in csv, %d excluded, %d already done, %d to process now",
             n_in_csv, n_excluded, len(done & set(entities)), len(pending))

    client = AsyncOpenAI(base_url=EDEN_BASE_URL, api_key=api_key)
    stats = asyncio.run(run(pending, args, client))

    n_rows = export_csv(jsonl, Path(args.out).with_suffix(".csv"))
    totals = Counter(r["status"] for r in last_records(jsonl).values())
    summary = {"entities_in_csv": n_in_csv, "excluded_example_entities": n_excluded,
               "already_done_before_run": len(done & set(entities)),
               "pending_before_limit": n_pending_total,
               "this_run": dict(stats),
               "all_runs_last_status": dict(totals),  # across every run, from the JSONL
               "csv_rows_total": n_rows}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()