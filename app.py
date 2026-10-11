"""World Cup Data Chat: ask football questions in plain English.

    streamlit run app.py
"""
import sys
from pathlib import Path
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from agent import ask  # noqa: E402

st.set_page_config(page_title="World Cup Data Chat", page_icon="⚽", layout="centered")
st.title("World Cup Data Chat")
st.caption("Ask anything about men's World Cups 1930–2022 and women's 1991–2019. "
           "The AI writes a database query, runs it, and shows you the answer and the query.")

EXAMPLES = ["Who has scored the most men's World Cup goals?",
            "Show goals per match for every men's World Cup",
            "How many matches has Saudi Arabia won at the World Cup?",
            "Which teams have the most yellow cards?"]
cols = st.columns(2)
for i, ex in enumerate(EXAMPLES):
    if cols[i % 2].button(ex, use_container_width=True):
        st.session_state["q"] = ex

q = st.text_input("Your question", key="q", placeholder="e.g. Who won the Golden Boot in 2014?")
if q:
    with st.spinner("Writing and running the query…"):
        try:
            r = ask(q)
        except Exception as e:
            st.error(f"Couldn't reach the AI model: {e}")
            st.stop()
    if r["error"]:
        st.error(f"The query didn't work: {r['error']}")
    else:
        df = pd.DataFrame(r["rows"], columns=r["columns"])
        if df.empty:
            st.info("No results for that question.")
        elif df.shape == (1, 1):
            st.metric(label=r["columns"][0], value=df.iat[0, 0])
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
            num = df.select_dtypes("number").columns
            text = [c for c in df.columns if c not in num]
            if len(num) >= 1 and 2 <= len(df) <= 60:
                label = text[0] if text else df.columns[0]
                st.bar_chart(df.set_index(df[label].astype(str))[num[-1]])
    with st.expander("Show the SQL"):
        st.code(r["sql"] or "", language="sql")

st.divider()
st.caption("Data: Fjelstul World Cup Database © 2023 Joshua C. Fjelstul, Ph.D., CC-BY-SA 4.0 "
           "(github.com/jfjelstul/worldcup), with added year/womens columns.")
