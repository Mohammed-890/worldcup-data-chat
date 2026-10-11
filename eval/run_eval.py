"""Score the app on the 50 test questions.

    python3 eval/run_eval.py                     # default model
    python3 eval/run_eval.py openai/gpt-4o       # any OpenRouter model id
Writes eval/results_<model>.json and prints accuracy."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "eval")]
from agent import ask, connect, backend  # noqa: E402
from compare import matches  # noqa: E402
from questions import QUESTIONS  # noqa: E402


def main(model=None):
    con, results = connect(), []
    print("Using:", backend(), model or "")
    for q, gold_sql in QUESTIONS:
        gold = con.execute(gold_sql).fetchall()
        try:
            r = ask(q, model)
            ok = r["error"] is None and matches(gold, r["rows"])
        except Exception as e:
            r, ok = {"sql": None, "error": f"{type(e).__name__}: {e}", "rows": []}, False
        results.append({"question": q, "correct": ok, "sql": r["sql"], "error": r["error"],
                        "gold": [list(x) for x in gold], "answer": [list(x) for x in r["rows"][:10]]})
        print("✓" if ok else "✗", q)
    acc = sum(x["correct"] for x in results)
    name = (model or backend()).replace("/", "_")
    (ROOT / f"eval/results_{name}.json").write_text(json.dumps(
        {"model": model, "correct": acc, "total": len(results), "results": results}, indent=1, ensure_ascii=False))
    print(f"\n{acc}/{len(results)} correct ({acc / len(results):.0%})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
