import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "eval")]
from agent import ask, connect, is_safe_select, extract_sql  # noqa: E402
from compare import matches  # noqa: E402
from questions import QUESTIONS  # noqa: E402


def test_all_gold_queries_run_and_return_rows():
    con = connect()
    assert len(QUESTIONS) == 50
    for q, sql in QUESTIONS:
        assert con.execute(sql).fetchall(), q


def test_known_facts():
    con = connect()
    assert con.execute(dict(QUESTIONS)["Which country has won the most men's World Cups?"]).fetchall() == [("Brazil", 5)]
    assert con.execute(dict(QUESTIONS)["How many goals did Miroslav Klose score at men's World Cups?"]).fetchall() == [(16,)]


def test_safety_guard():
    assert is_safe_select("SELECT * FROM goals")
    assert is_safe_select("with x as (select 1) select * from x;")
    assert not is_safe_select("DROP TABLE goals")
    assert not is_safe_select("SELECT 1; DELETE FROM goals")
    assert not is_safe_select("PRAGMA table_info(goals)")


def test_extract_sql():
    assert extract_sql("```sql\nSELECT 1;\n```") == "SELECT 1"
    assert extract_sql("SELECT 2") == "SELECT 2"


def test_compare():
    assert matches([("Brazil", 5)], [(5, "Brazil")])                       # column order
    assert matches([("Brazil",)], [("Brazil", 5)])                          # extra column ok
    assert matches([(1, "France"), (2, "Croatia")], [(2, "Croatia"), (1, "France")])
    assert not matches([("Brazil", 5)], [("Germany", 4)])
    assert not matches([(1,)], [(1,), (2,)])                                # extra wrong row
    assert matches([(9,)], [("A v B", 9), ("C v D", 9)])                    # ties listed
    assert matches([("Messi",), ("Mbappé",)], [("Messi", 23), ("Mbappé", 80), ("Messi", 108)])
    assert not matches([("Messi",), ("Mbappé",)], [("Messi", 23)])          # missing a scorer
    assert matches([(5.38,)], [(5.38,)]) and not matches([(5.38,)], [(5.40,)])


def test_ask_with_fake_model_and_retry():
    calls = []

    def fake(msgs, model):
        calls.append(msgs[-1]["content"])
        return "```sql\nSELECT nope FROM goals\n```" if len(calls) == 1 else \
               "```sql\nSELECT winner, COUNT(*) n FROM tournaments WHERE womens=0 GROUP BY winner ORDER BY n DESC LIMIT 1\n```"

    r = ask("most titles?", llm_fn=fake)
    assert r["error"] is None and r["attempts"] == 2 and r["rows"] == [("Brazil", 5)]
    assert "failed" in calls[-1]


def test_ask_refuses_writes():
    r = ask("delete everything", llm_fn=lambda m, mo: "DELETE FROM goals")
    assert r["error"].startswith("Refused")
