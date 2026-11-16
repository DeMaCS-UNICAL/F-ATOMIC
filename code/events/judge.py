import asyncio
import csv
import json
from pathlib import Path

from json_repair import repair_json

from events.prompts import JUDGE_PROMPT, JUDGE_SYSTEM_PROMPT
from config.settings import settings
from core.generator import UnifiedGenerator
from core.llm_providers import InvalidLLMResponse
from core.logger import log


class MultiJudgeSystem:
    """Approve unchanged annotations with at least two approvals and mean score >= 50."""

    def __init__(self, generator: UnifiedGenerator, judgement_file: str | None = None):
        self.gen = generator
        self._judge_panel = settings.judge_panel()
        if settings.JUDGE_SEMAPHORE_LIMIT <= 0:
            raise ValueError("JUDGE_SEMAPHORE must be positive.")
        # Fail locally before writing a log or starting any event/API calls.
        for provider, model in self._judge_panel:
            self.gen.validate_configuration(provider, model)
        self.semaphores = {
            provider: asyncio.Semaphore(settings.JUDGE_SEMAPHORE_LIMIT)
            for provider, _ in self._judge_panel
        }
        self.judgement_file = Path(judgement_file or settings.JUDGEMENT_FILE)
        self.columns = [
            "original_row_id", "event", "status", "score_avg_all",
            "score_avg_approvers", "approvals_count", "majority_vote",
        ] + [
            f"judge{slot}_{field}"
            for slot in range(1, 4)
            for field in ("provider", "model", "vote", "score", "reason")
        ]
        if self.judgement_file.exists():
            with self.judgement_file.open(newline="", encoding="utf-8-sig") as source:
                header = next(csv.reader(source), None)
            if header != self.columns:
                raise ValueError(
                    f"Incompatible judgment log header: {self.judgement_file}. "
                    "Select a new log file; existing files are not modified."
                )
        else:
            self.judgement_file.parent.mkdir(parents=True, exist_ok=True)
            with self.judgement_file.open("x", newline="", encoding="utf-8") as destination:
                csv.writer(destination).writerow(self.columns)

    async def _call_judge(self, provider: str, model: str, event: str, data: dict) -> dict:
        detail = {"provider": provider, "model": model}
        async with self.semaphores[provider]:
            compact = {
                "event": data.get("resolved_event", event),
                "crime": f"{data.get('crime_category', '')} / {data.get('crime_subcategory', '')}",
                "context": data.get("brief_context", ""),
                "xIntent": data.get("xIntent", []),
                "xAttr": data.get("xAttr", []),
                "xEffect": data.get("xEffect", []),
                "oEffect": data.get("oEffect", []),
            }
            prompt = JUDGE_PROMPT.format(event=compact["event"], prediction=json.dumps(compact))
            try:
                response = await self.gen.generate(provider, model, prompt, system_prompt=JUDGE_SYSTEM_PROMPT)
            except InvalidLLMResponse as exc:
                log.warning("Judge %s/%s returned an invalid API response (no retry): %s", provider, model, exc)
                return dict(detail, vote="error", score=0, reason=f"response_error: {exc}")
            except Exception as exc:
                # The generator has already exhausted retries or identified a permanent failure.
                log.warning("Judge %s/%s API call failed; counting score=0: %s", provider, model, exc)
                return dict(detail, vote="error", score=0, reason=f"api_error: {exc}")
            try:
                result = json.loads(repair_json(response))
                if not isinstance(result, dict):
                    raise ValueError("Expected a JSON object.")
                vote = result["vote"].lower()
                raw_score = result["score"]
                if isinstance(raw_score, bool):
                    raise ValueError("A numeric score is required.")
                score = int(raw_score)
                if vote not in {"approve", "reject"} or not 0 <= score <= 100:
                    raise ValueError("Expected vote approve/reject and score between 0 and 100.")
                return dict(detail, vote=vote, score=score, reason=str(result.get("reason", "No reason provided")))
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
                log.warning("Judge %s/%s verdict validation failed (no retry): %s", provider, model, exc)
                return dict(detail, vote="error", score=0, reason=f"validation_error: {exc}")

    async def evaluate_event(self, event: str, data: dict, original_row_id: int = -1):
        """Return (True, original data) or (False, None) after exactly one voting round."""
        results = await asyncio.gather(*(
            self._call_judge(provider, model, event, data)
            for provider, model in self._judge_panel
        ))
        approvals = sum(result["vote"] == "approve" for result in results)
        average = sum(result["score"] for result in results) / 3
        approved = approvals >= 2 and average >= 50
        self._log_verdict(original_row_id, event, "APPROVED" if approved else "REJECTED", results)
        return (True, data) if approved else (False, None)

    def _log_verdict(self, original_row_id: int, event: str, status: str, details: list[dict]):
        approvals = [result for result in details if result["vote"] == "approve"]
        row = [
            original_row_id, event, status,
            round(sum(result["score"] for result in details) / 3, 2),
            round(sum(result["score"] for result in approvals) / len(approvals), 2) if approvals else 0,
            len(approvals), len(approvals) >= 2,
        ]
        for detail in details:
            row.extend(detail[field] for field in ("provider", "model", "vote", "score", "reason"))
        with self.judgement_file.open("a", newline="", encoding="utf-8") as destination:
            csv.writer(destination).writerow(row)
