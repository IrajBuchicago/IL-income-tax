import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="IL Income Tax Dashboard", layout="wide")
st.title("Illinois Income Tax (INC) — Municipality Dashboard (2012–2025)")

# ---------------------------------------------------
# DATA LOADING
# ---------------------------------------------------

DATA_PATH = Path("il_income_tax_INC_only_fy2012_2025.csv")

st.write("Running from:", os.getcwd())

if not DATA_PATH.exists():
    st.error("CSV file not found. Make sure it is in the same folder as app.py.")
    st.stop()

@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]

    df["fy"] = pd.to_numeric(df["fy"], errors="coerce")
    df["fy_total"] = pd.to_numeric(df["fy_total"], errors="coerce")
    df["local_government"] = df["local_government"].astype(str).str.strip()
    df["tax"] = df["tax"].astype(str).str.strip().str.upper()

    df = df.dropna(subset=["fy", "fy_total"])
    df["fy"] = df["fy"].astype(int)

    # Keep INC only
    df = df[df["tax"] == "INC"].copy()

    return df.sort_values(["local_government", "fy"])

df = load_data(DATA_PATH)

st.success(f"Loaded {len(df)} rows | {df['local_government'].nunique()} municipalities")

# ---------------------------------------------------
# TABS
# ---------------------------------------------------

tab_chart, tab_table = st.tabs(["📈 Chart", "📊 Table"])

# ===================================================
# CHART TAB
# ===================================================
with tab_chart:

    municipalities = sorted(df["local_government"].unique())

    muni = st.selectbox("Select Municipality", municipalities)

    min_year = int(df["fy"].min())
    max_year = int(df["fy"].max())

    year_range = st.slider(
        "Select Year Range",
        min_year,
        max_year,
        (min_year, max_year)
    )

    d = df[
        (df["local_government"] == muni) &
        (df["fy"].between(year_range[0], year_range[1]))
    ].copy()

    fig = px.line(
        d,
        x="fy",
        y="fy_total",
        markers=True,
        title=f"{muni} — Income Tax Total (INC)"
    )

    fig.update_xaxes(dtick=1)
    fig.update_yaxes(tickformat=",.0f")  # comma formatting
    fig.update_traces(
        hovertemplate="FY %{x}<br>Total %{y:,.0f}<extra></extra>"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "Download Chart Data",
        d.to_csv(index=False).encode("utf-8"),
        file_name="chart_data.csv",
        mime="text/csv"
    )

# ===================================================
# TABLE TAB
# ===================================================
with tab_table:

    years = sorted(df["fy"].unique())
    year = st.selectbox("Select Fiscal Year", years, index=len(years) - 1)

    name_filter = st.text_input("Filter Municipality Name (contains)")

    t = df[df["fy"] == year][["local_government", "tax", "fy_total"]].copy()

    if name_filter:
        t = t[t["local_government"].str.contains(name_filter, case=False)]

    t = t.sort_values("fy_total", ascending=False)

    t["fy_total"] = t["fy_total"].round(0)

    st.dataframe(t, use_container_width=True, height=650)

    st.download_button(
        f"Download FY{year} Table",
        t.to_csv(index=False).encode("utf-8"),
        file_name=f"income_tax_INC_FY{year}.csv",
        mime="text/csv"
    )
