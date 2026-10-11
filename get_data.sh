#!/usr/bin/env bash
# Downloads the Fjelstul World Cup Database CSVs and builds data/worldcup.db.
set -euo pipefail
mkdir -p data/raw
for t in tournaments teams matches goals players player_appearances tournament_standings bookings award_winners stadiums; do
  curl -sSL -o "data/raw/$t.csv" "https://raw.githubusercontent.com/jfjelstul/worldcup/master/data-csv/$t.csv"
done
python3 src/build_db.py
