"""Turn a football question into SQL, run it safely, and return the result.

Two ways to reach an AI model:
  1. No key needed: if Claude Code is installed and signed in, it is used automatically
     (`claude -p`). This uses your Claude plan's usage.
  2. OpenRouter (any model):  export OPENROUTER_API_KEY=...  and optionally
     export WC_MODEL=openai/gpt-4o   (confirm ids on openrouter.ai/models)
"""
import json, os, re, shutil, sqlite3, subprocess
from pathlib import Path
from urllib import request

DB = Path(__file__).resolve().parents[1] / "data/worldcup.db"
API = "https://openrouter.ai/api/v1/chat/completions"
MAX_ROWS = 200

NOTES = """Notes:
- Every tournament-level table has `year` and `womens` (0 = men's World Cup, 1 = women's). If a question
  doesn't say men's or women's, assume men's (womens = 0).
- Data covers men's World Cups 1930-2022 and women's 1991-2019. The 2026 World Cup is NOT included.
- goals: own_goal = 1 for own goals (credited to the opponent's team_name); penalty = 1 for penalty goals
  (not shootouts). Exclude own goals when counting a player's goals.
- matches: score is text like '3–3' (en dash); use home_team_score/away_team_score for numbers.
  penalty_shootout = 1 if decided on penalties; home_team_win/away_team_win/draw are 0/1.
- Some players have only one name (e.g. given_name = 'not applicable', family_name = 'Marta').
- bookings: sending_off = 1 for any red card (straight or second yellow)."""


def schema(con) -> str:
    lines = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
        lines.append(f"{t}({', '.join(cols)})")
    vals = {
        "matches.stage_name": "SELECT DISTINCT stage_name FROM matches",
        "award_winners.award_name": "SELECT DISTINCT award_name FROM award_winners",
        "goals.match_period": "SELECT DISTINCT match_period FROM goals",
    }
    for k, q in vals.items():
        lines.append(f"{k} values: " + ", ".join(repr(r[0]) for r in con.execute(q)))
    return "\n".join(lines)


def connect():
    # read-only, immutable: the app can never change the data
    return sqlite3.connect(f"file:{DB}?mode=ro&immutable=1", uri=True)


def is_safe_select(sql: str) -> bool:
    s = sql.strip().rstrip(";").strip()
    if ";" in s:
        return False
    return bool(re.match(r"(?is)^\s*(select|with)\b", s)) and not re.search(
        r"(?i)\b(insert|update|delete|drop|alter|create|attach|pragma|replace|vacuum)\b", s)


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def backend() -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if shutil.which("claude"):
        return "claude-cli"
    raise RuntimeError("No AI model available: sign in to Claude Code, or set OPENROUTER_API_KEY.")


def llm(messages, model=None) -> str:
    if backend() == "claude-cli":
        prompt = "\n\n".join(f"[{m['role'].upper()}]\n{m['content']}" for m in messages)
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            raise RuntimeError(f"claude -p failed: {r.stderr.strip()[:200]}")
        return r.stdout
    key = os.environ["OPENROUTER_API_KEY"]
    body = json.dumps({"model": model or os.environ.get("WC_MODEL", "anthropic/claude-sonnet-4.5"),
                       "temperature": 0, "messages": messages}).encode()
    req = request.Request(API, data=body, headers={"Authorization": f"Bearer {key}",
                                                    "Content-Type": "application/json"})
    with request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def ask(question: str, model=None, llm_fn=llm):
    """Returns dict(sql, columns, rows, error, attempts)."""
    con = connect()
    system = ("You write SQLite queries for a World Cup database. Reply with ONE SELECT query in a "
              "```sql``` block and nothing else.\n\nSchema:\n" + schema(con) + "\n\n" + NOTES)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    out = {"sql": None, "columns": [], "rows": [], "error": None, "attempts": 0}
    for attempt in range(2):          # one retry, showing the model its own error
        out["attempts"] = attempt + 1
        sql = extract_sql(llm_fn(msgs, model))
        out["sql"] = sql
        if not is_safe_select(sql):
            out["error"] = "Refused: only single read-only SELECT queries are allowed."
            return out
        try:
            cur = con.execute(sql)
            out["columns"] = [d[0] for d in cur.description]
            out["rows"] = cur.fetchmany(MAX_ROWS)
            out["error"] = None
            return out
        except sqlite3.Error as e:
            out["error"] = str(e)
            msgs += [{"role": "assistant", "content": f"```sql\n{sql}\n```"},
                     {"role": "user", "content": f"That query failed: {e}. Fix it."}]
    return out
