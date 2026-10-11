# World Cup Data Chat

Ask football questions in plain English. An AI model turns the question into SQL,
runs it on a database of every World Cup match, goal, card and award, and shows the
answer, a chart and the exact query it used.

> "How many matches has Saudi Arabia won at the World Cup?" → 4
> "Which men's World Cup had the most goals per match?" → 1954, 5.38 per match

**Coverage:** men's World Cups 1930–2022, women's 1991–2019. The 2026 tournament is not in the source data yet.

## How it works

1. **Database:** 10 tables (matches, goals, players, appearances, bookings, awards, standings, stadiums, teams, tournaments) in SQLite. I added `year` and `womens` columns to every tournament-level table so the model can filter easily.
2. **Prompt:** the model gets the table schema, example values for tricky columns, and notes on the data's quirks (own goals, penalty shootouts, scores stored as text, one-name players).
3. **Safety:** the database is opened read-only, and only a single `SELECT` is accepted, so a bad or malicious question can't change the data.
4. **Self-correction:** if the query errors, the model sees the error and gets one retry.
5. **Display:** single numbers as a metric, tables with an automatic bar chart, and the SQL in an expander.

## Accuracy

`eval/questions.py` has 50 questions with hand-written correct SQL, checked against real results
(Klose 16 goals, Messi 13, Brazil 5 titles, Morocco 4th in 2022). An answer counts as correct if it
finds every expected value and returns no wrong rows. Order, extra columns and repeated rows are
allowed, so listing all three 9-goal wins or naming Messi once per goal still counts.

| Model | Correct |
|---|---|
| Claude (via Claude Code CLI) | 50 / 50 (100%) |

The first run scored 47/50, but all 3 "misses" were correct answers that the checker rejected for
having more rows than expected (tied records, a player scoring twice). The checker was fixed and
the saved answers re-scored; no questions or answers were changed. 50 questions is a small test,
so treat this as "reliable on common questions", not "never wrong".

## Run

```bash
pip install -r requirements.txt
./get_data.sh                       # download data and build data/worldcup.db
export OPENROUTER_API_KEY=...       # openrouter.ai; one key for many models
streamlit run app.py
python3 eval/run_eval.py            # accuracy on the 50 test questions
python3 -m pytest -q tests          # tests, no API key needed
```

Set `WC_MODEL` to choose a model (default `anthropic/claude-sonnet-4.5`; confirm the id on openrouter.ai/models).

## Data and licence

Fjelstul World Cup Database © 2023 Joshua C. Fjelstul, Ph.D., [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/legalcode),
[github.com/jfjelstul/worldcup](https://www.github.com/jfjelstul/worldcup). Modified: removed id/link columns, added `year` and `womens`.
The database file in this repo is therefore also CC-BY-SA 4.0.
