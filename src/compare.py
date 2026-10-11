"""Decide whether the app's result matches the gold answer.

Correct = every gold row is found in the answer, and every answer row matches some
gold row. Extra columns are fine, row order doesn't matter, and repeated rows are fine
(e.g. a player listed once per goal, or every match tied for the record)."""
from collections import Counter


def norm(v):
    if isinstance(v, (int, float)):
        return f"{float(v):.2f}"
    return str(v).strip().lower()


def matches(gold_rows, pred_rows) -> bool:
    if not gold_rows or not pred_rows:
        return not gold_rows and not pred_rows
    gold = [Counter(norm(v) for v in g) for g in gold_rows]
    pred = [Counter(norm(v) for v in r) for r in pred_rows]
    fits = lambda g, p: not (g - p)
    return all(any(fits(g, p) for p in pred) for g in gold) and \
        all(any(fits(g, p) for g in gold) for p in pred)
