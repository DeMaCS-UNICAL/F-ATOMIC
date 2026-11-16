from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


THRESHOLDS = (50, 60)
KEY = ["original_row_id", "event"]


def repository_root() -> Path:
    for path in Path(__file__).resolve().parents:
        if (path / "pyproject.toml").is_file():
            return path
    raise FileNotFoundError("Cannot locate the repository; pass --root explicitly.")


def require_columns(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{name}: missing columns {missing}")


def normalize_decisions(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    require_columns(frame, KEY + ["status", "score_avg_all"], name)
    frame["status"] = frame["status"].astype("string").str.strip().str.upper()
    frame["score_avg_all"] = pd.to_numeric(frame["score_avg_all"], errors="coerce")
    frame["llm_approved"] = frame["status"].map({"APPROVED": True, "REJECTED": False}).astype("boolean")
    if frame["llm_approved"].isna().any():
        raise ValueError(f"{name}: status must be APPROVED or REJECTED")
    return frame


def read_judgments(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"original_row_id": "string"}, low_memory=False)
    frame = normalize_decisions(frame, str(path))
    if "approvals_count" in frame:
        frame["approvals_count"] = pd.to_numeric(frame["approvals_count"], errors="coerce")
    return frame


def unique_judgments(judged: pd.DataFrame) -> pd.DataFrame:
    counts = judged.groupby(KEY, dropna=False).size().rename("matching_log_rows").reset_index()
    unique = judged.merge(counts, on=KEY, validate="m:1")
    return unique.loc[unique["matching_log_rows"].eq(1), KEY + ["status", "score_avg_all", "llm_approved"]]


def read_human_csv(
    path: Path, judged: pd.DataFrame | None = None, *, llm_source: str = "auto",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read event or form-event aggregates without assumptions about cohort size.

    In auto mode, embedded LLM decisions are retained when present (as in the
    supplied original comparison); otherwise they are joined from the log.
    Repeated human event keys are allowed, but a log match must be unique.
    """
    frame = pd.read_csv(path, dtype={"original_row_id": "string", "form_id": "string"}, low_memory=False)
    require_columns(frame, KEY + ["human_score", "human_approval_pct"], str(path))
    if frame.empty:
        raise ValueError(f"{path}: no human evaluations")
    if frame[KEY].isna().any().any():
        raise ValueError(f"{path}: event keys must not be missing")
    for column in ("human_score", "human_approval_pct"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    embedded = llm_source == "embedded" or (llm_source == "auto" and {"status", "score_avg_all"}.issubset(frame.columns))
    if embedded:
        frame = normalize_decisions(frame, str(path))
    if judged is None and not embedded:
        raise ValueError(f"{path}: supply --judge-csv or embedded status and score_avg_all columns")
    audit_row = {
        "source_rows": len(frame),
        "unique_events": frame[KEY].drop_duplicates().shape[0],
        "llm_source": "embedded" if embedded else "log",
        "matched_log_rows": pd.NA,
        "unmatched_or_nonunique_log_rows": pd.NA,
        "status_disagreements": pd.NA,
        "score_disagreements_above_0_11": pd.NA,
    }
    if judged is None:
        return frame, pd.DataFrame([audit_row])
    log = unique_judgments(judged).rename(columns={"status": "log_status", "score_avg_all": "log_score", "llm_approved": "log_approved"})
    matched = frame.merge(log, on=KEY, how="left", validate="m:1")
    missing = matched["log_status"].isna()
    audit_row.update({
        "matched_log_rows": int((~missing).sum()),
        "unmatched_or_nonunique_log_rows": int(missing.sum()),
    })
    if not embedded:
        if missing.any():
            raise ValueError(f"{path}: {int(missing.sum())} human rows lack a unique LLM log match on {KEY}")
        frame = matched.drop(columns=["status", "score_avg_all", "llm_approved"], errors="ignore").rename(columns={
            "log_status": "status", "log_score": "score_avg_all", "log_approved": "llm_approved",
        })
        frame["llm_approved"] = frame["llm_approved"].astype("boolean")
        audit_row.update({"status_disagreements": 0, "score_disagreements_above_0_11": 0})
    else:
        audit_row.update({
            "status_disagreements": int((~missing & matched["status"].ne(matched["log_status"])).fillna(False).sum()),
            "score_disagreements_above_0_11": int((matched["score_avg_all"] - matched["log_score"]).abs().gt(0.11).sum()),
        })
    return frame, pd.DataFrame([audit_row])


def comparison(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for measure in ("human_score", "human_approval_pct", "human_score_and_approval_pct_ge_50"):
        for threshold in THRESHOLDS:
            columns = ["human_score", "human_approval_pct"] if measure == "human_score_and_approval_pct_ge_50" else [measure]
            valid = frame[columns + ["llm_approved"]].dropna()
            if measure == "human_score_and_approval_pct_ge_50":
                human = (valid["human_score"].ge(threshold) & valid["human_approval_pct"].ge(50)).to_numpy(dtype=bool)
            else:
                human = valid[measure].ge(threshold).to_numpy(dtype=bool)
            llm = valid["llm_approved"].to_numpy(dtype=bool)
            tp = int(np.sum(human & llm))
            tn = int(np.sum(~human & ~llm))
            fp = int(np.sum(~human & llm))
            fn = int(np.sum(human & ~llm))
            n = len(valid)
            agreement = (tp + tn) / n if n else np.nan
            expected = (human.mean() * llm.mean() + (1 - human.mean()) * (1 - llm.mean())) if n else np.nan
            precision = tp / (tp + fp) if tp + fp else np.nan
            recall = tp / (tp + fn) if tp + fn else np.nan
            f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else np.nan
            rows.append({
                "human_measure": measure, "threshold": threshold, "n": n,
                "human_approval_pct": round(100 * human.mean(), 2) if n else np.nan,
                "llm_approval_pct": round(100 * llm.mean(), 2) if n else np.nan,
                "agreement_pct": round(100 * agreement, 2) if n else np.nan,
                "cohen_kappa": round((agreement - expected) / (1 - expected), 3) if n and expected < 1 else np.nan,
                "precision_vs_human": round(precision, 3), "recall_vs_human": round(recall, 3),
                "f1_vs_human": round(f1, 3), "tp": tp, "tn": tn, "fp": fp, "fn": fn,
            })
    return pd.DataFrame(rows)


def form_observations(frame: pd.DataFrame) -> pd.DataFrame:
    observations = []
    for row in frame.itertuples(index=False):
        if pd.isna(row.individual_responses_json):
            continue
        responses = json.loads(row.individual_responses_json)
        if not isinstance(responses, list) or any(not isinstance(response, dict) for response in responses):
            raise ValueError("individual_responses_json must contain lists of response objects")
        for response in responses:
            number = response.get("form_number")
            if number is None:
                number = response.get("form_id")
            if number is None:
                continue
            if "human_score" in response:
                score = pd.to_numeric(response["human_score"], errors="coerce")
            else:
                score = pd.to_numeric(response.get("score_0_10"), errors="coerce") * 10
            decision = str(response.get("decision", "")).strip().upper()
            observations.append({
                "form_number": number, "original_row_id": row.original_row_id, "event": row.event,
                "human_score": float(score) if pd.notna(score) else np.nan,
                "decision": decision if decision in {"APPROVE", "REJECT"} else None,
                "llm_approved": row.llm_approved,
            })
    data = pd.DataFrame(observations)
    if data.empty:
        return data
    group = ["form_number"] + KEY
    per_event = data.groupby(group, dropna=False).agg(
        human_score=("human_score", "mean"),
        approvals=("decision", lambda values: sum(v == "APPROVE" for v in values)),
        decisions=("decision", lambda values: sum(v in {"APPROVE", "REJECT"} for v in values)),
        responses=("decision", "size"),
        llm_approved=("llm_approved", "first"),
    ).reset_index()
    per_event["human_approval_pct"] = np.where(per_event["decisions"].gt(0), 100 * per_event["approvals"] / per_event["decisions"], np.nan)
    return per_event


def by_form(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = []
    for form, subset in frame.groupby(column, dropna=False):
        for record in comparison(subset).to_dict("records"):
            rows.append({"form_id": form, "event_rows": len(subset), **record})
    return pd.DataFrame(rows)


def by_category(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, subset in frame.dropna(subset=["crime_category"]).groupby("crime_category"):
        for record in comparison(subset).to_dict("records"):
            rows.append({"crime_category": category, "event_rows": len(subset), **record})
    return pd.DataFrame(rows)


def add_categories(frame: pd.DataFrame, path: Path | None) -> pd.DataFrame:
    if "crime_category" in frame or path is None:
        return frame
    atomic = pd.read_csv(path, dtype={"original_row_id": "string"}, usecols=KEY + ["crime_category"])
    groups = atomic.groupby(KEY, dropna=False)["crime_category"].agg(["nunique", "first"]).reset_index()
    groups.loc[groups["nunique"].ne(1), "first"] = pd.NA
    return frame.merge(groups[KEY + ["first"]].rename(columns={"first": "crime_category"}), on=KEY, how="left", validate="m:1")


def summary(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    valid = frame[["human_score", "score_avg_all"]].dropna()
    return pd.DataFrame([{
        "cohort": name, "rows": len(frame), "unique_events": frame[KEY].drop_duplicates().shape[0],
        "mean_human_score": round(frame["human_score"].mean(), 2),
        "mean_llm_score": round(frame["score_avg_all"].mean(), 2),
        "mean_absolute_score_difference": round((valid["human_score"] - valid["score_avg_all"]).abs().mean(), 2),
        "llm_approval_pct": round(100 * frame["llm_approved"].dropna().astype(bool).mean(), 2),
    }])


def style_figure(fig: plt.Figure) -> None:
    """Keep exported figures readable regardless of the notebook theme."""
    dark = "#202124"
    fig.patch.set_facecolor("white")
    for ax in fig.axes:
        ax.set_facecolor("white")
        ax.title.set_color(dark)
        ax.xaxis.label.set_color(dark)
        ax.yaxis.label.set_color(dark)
        ax.tick_params(colors=dark)
        for spine in ax.spines.values():
            spine.set_color(dark)
        legend = ax.get_legend()
        if legend is not None:
            legend.get_frame().set_facecolor("white")
            legend.get_frame().set_edgecolor("#b0b0b0")
            for label in legend.get_texts():
                label.set_color(dark)
    if fig._suptitle is not None:
        fig._suptitle.set_color(dark)


def save_figure(table: pd.DataFrame, destination: Path, label: str) -> None:
    measures = (
        ("human_score", "Human score"),
        ("human_approval_pct", "Human approval (%)"),
        ("human_score_and_approval_pct_ge_50", "Score and approval >= 50%"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, (measure, title) in zip(axes, measures):
        subset = table.loc[table["human_measure"].eq(measure)]
        positions = np.arange(len(subset))
        ax.bar(positions - 0.18, subset["human_approval_pct"], width=0.36, label="Human", color="#2a6fbb")
        ax.bar(positions + 0.18, subset["llm_approval_pct"], width=0.36, label="LLM", color="#c05a21")
        ax.set_xticks(positions, subset["threshold"].astype(str))
        ax.set_ylim(0, 100)
        ax.set_xlabel("Threshold")
        ax.set_ylabel("Approval (%)")
        ax.set_title(title)
        ax.legend()
    fig.suptitle(label)
    style_figure(fig)
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=150, facecolor="white")
    plt.close(fig)


def save_confusion_figures(table: pd.DataFrame, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for row in table.itertuples(index=False):
        matrix = np.array([[row.tn, row.fp], [row.fn, row.tp]])
        fig, ax = plt.subplots(figsize=(5, 4))
        image = ax.imshow(matrix, cmap="Blues")
        ax.set_xticks([0, 1], ["Rejected", "Approved"])
        ax.set_yticks([0, 1], ["Not confirmed", "Confirmed"])
        ax.set_xlabel("LLM decision (official)")
        ax.set_ylabel("Human decision")
        if row.human_measure == "human_score_and_approval_pct_ge_50":
            ax.set_title(f"LLM vs human decisions\nScore >= {row.threshold} and approval >= 50%")
        else:
            ax.set_title(f"LLM vs human decisions\n{row.human_measure.replace('_', ' ').title()} >= {row.threshold}")
        for (i, j), value in np.ndenumerate(matrix):
            red, green, blue, _ = image.cmap(image.norm(value))
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            ax.text(j, i, str(int(value)), ha="center", va="center",
                    color="#202124" if luminance > 0.5 else "white")
        style_figure(fig)
        fig.tight_layout()
        fig.savefig(destination / f"confusion_{row.human_measure}_{row.threshold}.png", dpi=150, facecolor="white")
        plt.close(fig)


def save_scores_figure(frame: pd.DataFrame, destination: Path, label: str) -> None:
    data = frame[["human_score", "score_avg_all"]].dropna()
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(data["human_score"], data["score_avg_all"], s=12, alpha=0.35, color="#2a6fbb")
    ax.plot([0, 100], [0, 100], color="black", linewidth=1)
    ax.set(xlim=(0, 100), ylim=(0, 100), xlabel="Mean human score", ylabel="Mean LLM score", title=label)
    style_figure(fig)
    fig.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=150, facecolor="white")
    plt.close(fig)


def llm_tables(judged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables = {
        "llm_overview": pd.DataFrame([{
            "log_rows": len(judged),
            "approved": int(judged["llm_approved"].sum()),
            "rejected": int((~judged["llm_approved"]).sum()),
            "mean_llm_score": round(judged["score_avg_all"].mean(), 2),
        }]),
    }
    if "approvals_count" in judged:
        tables["llm_votes"] = judged.groupby("approvals_count", dropna=False).size().rename("rows").reset_index()
        tables["llm_policy_50_60"] = pd.DataFrame([{
            "threshold": threshold,
            "majority_and_score_approval_rows": int((judged["approvals_count"].ge(2) & judged["score_avg_all"].ge(threshold)).sum()),
            "score_only_approval_rows": int(judged["score_avg_all"].ge(threshold).sum()),
            "recorded_approval_rows": int(judged["llm_approved"].sum()),
            "total_rows": len(judged),
        } for threshold in THRESHOLDS])
    provider_rows = []
    for slot in (1, 2, 3):
        provider_col, vote_col, score_col = (f"judge{slot}_provider", f"judge{slot}_vote", f"judge{slot}_score")
        if {provider_col, vote_col, score_col}.issubset(judged.columns):
            provider_rows.append(judged[[provider_col, vote_col, score_col]].rename(columns={
                provider_col: "provider", vote_col: "vote", score_col: "score",
            }))
    if provider_rows:
        providers = pd.concat(provider_rows, ignore_index=True)
        providers["score"] = pd.to_numeric(providers["score"], errors="coerce")
        providers["vote"] = providers["vote"].astype("string").str.strip().str.lower()
        stats = providers.groupby("provider", dropna=False).agg(
            votes=("vote", "size"), approvals=("vote", lambda v: int(v.eq("approve").sum())),
            mean_score=("score", "mean"),
        ).reset_index()
        stats["mean_score"] = stats["mean_score"].round(2)
        tables["llm_provider_statistics"] = stats
    return tables


def run(
    root: Path | None = None, *,
    human_csvs: dict[str, Path] | None = None,
    judge_csv: Path | None = None,
    dataset_csv: Path | None = None,
    output_dir: Path | None = None,
    llm_source: str = "auto",
) -> dict[str, pd.DataFrame]:
    """Analyze any named cohorts; omitted inputs select the supplied archive.

    Relative paths resolve against root. Custom runs write to <output_dir>/<cohort>/;
    the no-argument archive preset retains its original paths
    and table keys. No cohort names or row counts are required for custom runs.
    """
    root = Path(root).resolve() if root is not None else repository_root()

    def resolve(value: Path) -> Path:
        return root / Path(value).expanduser()

    archived = human_csvs is None
    if archived:
        human_csvs = {
            "historical": Path("human_validation/events/data/global_comparison_results.csv"),
            "unified": Path("human_validation/events/data/unified_human_judgments.csv"),
        }
        if judge_csv is None:
            judge_csv = Path("experiments/events/results/tribunal_judgments.csv")
        if dataset_csv is None:
            dataset_csv = Path("experiments/events/results/forensic_atomic_tribunal_validated.csv")
    if not human_csvs:
        raise ValueError("Supply at least one human CSV")
    if llm_source not in {"auto", "log", "embedded"}:
        raise ValueError("llm_source must be auto, log or embedded")
    for name in human_csvs:
        if not name or name in {".", ".."} or any(c in name for c in "/\\"):
            raise ValueError(f"Cohort names must be single directory names: {name!r}")
    output = resolve(output_dir if output_dir is not None else Path("human_validation/events/results"))
    dataset_path = resolve(dataset_csv) if dataset_csv is not None else None
    judged = read_judgments(resolve(judge_csv)) if judge_csv is not None else None
    tables = llm_tables(judged) if judged is not None else {}
    destinations = {}
    frames = {}
    for name, path in human_csvs.items():
        frame, audit = read_human_csv(resolve(path), judged, llm_source=llm_source)
        frame = add_categories(frame, dataset_path)
        frames[name] = frame
        audit["category_mapped_rows"] = int(frame["crime_category"].notna().sum()) if "crime_category" in frame else 0
        tables[f"{name}/summary"] = summary(frame, name)
        tables[f"{name}/comparison_50_60"] = comparison(frame)
        tables[f"{name}/match_audit"] = audit
        observations = form_observations(frame) if "individual_responses_json" in frame else pd.DataFrame()
        if not observations.empty:
            tables[f"{name}/form_event_observations"] = observations
            tables[f"{name}/by_form_50_60"] = by_form(observations, "form_number")
        elif "form_id" in frame:
            tables[f"{name}/by_form_50_60"] = by_form(frame, "form_id")
        if "crime_category" in frame:
            tables[f"{name}/by_category_50_60"] = by_category(frame)
        destinations[name] = output / (
            "form_results_v1" if name == "historical" else "form_results_v2/unified"
        ) if archived else output / name
    for name, table in tables.items():
        if "/" in name:
            cohort, filename = name.split("/", 1)
            destination = destinations[cohort] / f"{filename}.csv"
        else:
            destination = (output / "form_results_v2" if archived else output) / f"{name}.csv"
        destination.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(destination, index=False, encoding="utf-8-sig")
    for name, destination in destinations.items():
        label = name.replace("_", " ").title()
        save_figure(tables[f"{name}/comparison_50_60"], destination / "approval_50_60.png", f"{label} human and LLM decisions")
        save_confusion_figures(tables[f"{name}/comparison_50_60"], destination / "figures")
        save_scores_figure(frames[name], destination / "score_comparison.png", f"{label} score comparison")
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=None, help="Base for relative paths (default: script's repository)")
    parser.add_argument("--human-csv", type=Path, action="append", help="Human aggregate CSV; repeat for multiple cohorts")
    parser.add_argument("--cohort", action="append", help="Output label for each --human-csv, in the same order; defaults to file stem")
    parser.add_argument("--judge-csv", type=Path, help="Recorded LLM judgments matched by original_row_id and event")
    parser.add_argument("--dataset-csv", type=Path, help="Optional category lookup with original_row_id, event, crime_category")
    parser.add_argument("--output-dir", type=Path, help="Report directory; use a separate directory for a new evaluation")
    parser.add_argument("--llm-source", choices=("auto", "log", "embedded"), default="auto",
                        help="auto keeps embedded LLM decisions if present, otherwise joins the log")
    args = parser.parse_args()
    if args.cohort and (not args.human_csv or len(args.cohort) != len(args.human_csv)):
        parser.error("Supply one --cohort per --human-csv, or omit all --cohort options")
    human_csvs = None
    if args.human_csv:
        names = args.cohort or [path.stem for path in args.human_csv]
        if len(names) != len(set(names)):
            parser.error("Cohort labels must be unique; use --cohort to distinguish identical file stems")
        human_csvs = dict(zip(names, args.human_csv))
    tables = run(args.root, human_csvs=human_csvs, judge_csv=args.judge_csv,
                 dataset_csv=args.dataset_csv, output_dir=args.output_dir, llm_source=args.llm_source)
    summaries = [table for name, table in tables.items() if name.endswith("/summary")]
    print(pd.concat(summaries, ignore_index=True).to_string(index=False))


if __name__ == "__main__":
    main()
