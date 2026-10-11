"""Build data/worldcup.db (SQLite) from the Fjelstul World Cup Database CSVs.

Data: © 2023 Joshua C. Fjelstul, Ph.D., CC-BY-SA 4.0, https://www.github.com/jfjelstul/worldcup
Modifications: dropped id/link columns, added `year` and `womens` columns to every
tournament-level table so questions like "men's World Cups since 1990" are easy to query.
"""
import sqlite3
import sys
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
DB = Path("data/worldcup.db")
TABLES = ["tournaments", "teams", "matches", "goals", "players", "player_appearances",
          "tournament_standings", "bookings", "award_winners", "stadiums"]
DROP = lambda cols: [c for c in cols if c == "key_id" or c.endswith("wikipedia_link")]


def main(db_path=DB):
    db_path = Path(db_path)
    tours = pd.read_csv(RAW / "tournaments.csv")
    tours["womens"] = tours["tournament_name"].str.contains("Women").astype(int)
    meta = tours[["tournament_id", "year", "womens"]]
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    for t in TABLES:
        df = tours if t == "tournaments" else pd.read_csv(RAW / f"{t}.csv")
        df = df.drop(columns=DROP(df.columns))
        if t != "tournaments" and "tournament_id" in df.columns:
            df = df.merge(meta, on="tournament_id", how="left")
        df.to_sql(t, con, index=False)
        print(f"{t:22s} {len(df):6,} rows")
    con.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else DB)
