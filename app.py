import os
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="IL Income Tax LGDF Dashboard", layout="wide")
st.title("Illinois Income Tax (INC) — Municipality LGDF Modeling Dashboard")

# ---------------------------------------------------
# ACTUAL EFFECTIVE LGDF RATES BY FISCAL YEAR
# ---------------------------------------------------
ACTUAL_EFFECTIVE_RATES = {
    2012: 6.00,
    2013: 6.00,
    2014: 6.00,
    2015: 6.00,
    2016: 8.00,
    2017: 8.00,
    2018: 5.45,
    2019: 5.75,
    2020: 5.75,
    2021: 6.06,
    2022: 6.06,
    2023: 6.16,
    2024: 6.47,
    2025: 6.47,
}

# ---------------------------------------------------
# DATA LOADING
# ---------------------------------------------------
DATA_PATH = Path("il_income_tax_INC_only_fy2012_2025.csv")

if not DATA_PATH.exists():
    st.error("CSV file not found. Make sure il_income_tax_INC_only_fy2012_2025.csv is in the same folder as app.py.")
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
    df = df[df["tax"] == "INC"].copy()
    return df.sort_values(["local_government", "fy"])


df = load_data(DATA_PATH)

# ---------------------------------------------------
# MODELED RATE CONTROL
# ---------------------------------------------------
st.success(f"Loaded {len(df)} rows | {df['local_government'].nunique()} municipalities")

st.header("LGDF Rate Modeling")
st.write("Use the slider below to set the modeled LGDF effective rate and compare against actual collections.")

modeled_rate = st.slider(
    "Modeled Effective Rate (%)",
    min_value=1.0,
    max_value=15.0,
    value=10.0,
    step=0.25,
    format="%.2f%%",
)

st.info(f"Currently modeling at **{modeled_rate:.2f}%**. Drag the slider above to change it.")
st.markdown("---")

# ---------------------------------------------------
# COMPUTE MODELED COLUMNS
# ---------------------------------------------------
df["actual_rate"] = df["fy"].map(ACTUAL_EFFECTIVE_RATES)
df["modeled_collection"] = df["fy_total"] * (modeled_rate / df["actual_rate"])
df["forgone_revenue"] = df["modeled_collection"] - df["fy_total"]
df["forgone_revenue"] = df["forgone_revenue"].clip(lower=0)
df["modeled_collection"] = df[["fy_total", "modeled_collection"]].max(axis=1)

# ---------------------------------------------------
# TABS
# ---------------------------------------------------
tab_bar, tab_chart, tab_top, tab_table = st.tabs(
    ["Bar Chart — Forgone Revenue", "Line Chart", "Top Municipalities", "Data Table"]
)

municipalities = ["All Municipalities"] + sorted(df["local_government"].unique())
min_year = int(df["fy"].min())
max_year = int(df["fy"].max())


def filter_data(dataframe, muni, year_range):
    """Filter by municipality and year range. If 'All Municipalities', aggregate by year."""
    filtered = dataframe[dataframe["fy"].between(year_range[0], year_range[1])].copy()
    if muni == "All Municipalities":
        agg = filtered.groupby("fy", as_index=False).agg(
            fy_total=("fy_total", "sum"),
            modeled_collection=("modeled_collection", "sum"),
            forgone_revenue=("forgone_revenue", "sum"),
        )
        agg["actual_rate"] = agg["fy"].map(ACTUAL_EFFECTIVE_RATES)
        agg["local_government"] = "All Municipalities"
        return agg
    else:
        return filtered[filtered["local_government"] == muni].copy()


# ===================================================
# BAR CHART TAB
# ===================================================
with tab_bar:
    col_muni2, col_years2 = st.columns([1, 2])
    with col_muni2:
        muni_bar = st.selectbox("Select Municipality", municipalities, key="muni_bar")
    with col_years2:
        year_range_bar = st.slider(
            "Select Year Range",
            min_year,
            max_year,
            (min_year, max_year),
            key="yr_bar",
        )

    d2 = filter_data(df, muni_bar, year_range_bar)

    fig_bar = go.Figure()

    fig_bar.add_trace(
        go.Bar(
            x=d2["fy"],
            y=d2["fy_total"],
            name="Actual Collection",
            marker_color="rgba(124, 179, 66, 0.5)",
            text=d2["fy_total"].apply(lambda v: f"${v:,.0f}"),
            textposition="inside",
            hovertemplate="FY %{x}<br>Actual: $%{y:,.0f}<extra></extra>",
        )
    )

    fig_bar.add_trace(
        go.Bar(
            x=d2["fy"],
            y=d2["forgone_revenue"],
            name="Forgone Revenue",
            marker_color="rgba(76, 175, 80, 0.9)",
            text=d2["forgone_revenue"].apply(lambda v: f"${v:,.0f}"),
            textposition="inside",
            hovertemplate="FY %{x}<br>Forgone: $%{y:,.0f}<extra></extra>",
        )
    )

    fig_bar.add_trace(
        go.Scatter(
            x=d2["fy"],
            y=d2["modeled_collection"],
            mode="text",
            text=d2["modeled_collection"].apply(lambda v: f"${v:,.0f}"),
            textposition="top center",
            textfont=dict(size=11, color="black"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig_bar.update_layout(
        barmode="stack",
        title=f"{muni_bar} — LGDF Modeling (Modeled Rate: {modeled_rate:.1f}%)",
        xaxis_title="Fiscal Year",
        yaxis_title="Collection ($)",
        yaxis_tickformat=",.0f",
        xaxis_dtick=1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("Forgone Revenue Impact")
    col1b, col2b, col3b, col4b = st.columns(4)
    sorted_d2 = d2.sort_values("fy", ascending=False)

    with col1b:
        latest = sorted_d2["forgone_revenue"].iloc[0] if len(sorted_d2) > 0 else 0
        st.metric("1-Year Impact", f"${latest:,.0f}")
    with col2b:
        three = sorted_d2.head(3)["forgone_revenue"].sum() if len(sorted_d2) >= 3 else sorted_d2["forgone_revenue"].sum()
        st.metric("3-Year Impact", f"${three:,.0f}")
    with col3b:
        five = sorted_d2.head(5)["forgone_revenue"].sum() if len(sorted_d2) >= 5 else sorted_d2["forgone_revenue"].sum()
        st.metric("5-Year Impact", f"${five:,.0f}")
    with col4b:
        total = d2["forgone_revenue"].sum()
        st.metric("Total Impact", f"${total:,.0f}")

    st.subheader("Rate Comparison")
    rate_table = d2[["fy", "actual_rate", "fy_total", "modeled_collection", "forgone_revenue"]].copy()
    rate_table["modeled_rate"] = modeled_rate
    rate_table["rate_difference"] = modeled_rate - rate_table["actual_rate"]
    rate_table.columns = [
        "Fiscal Year",
        "Actual Effective Rate (%)",
        "Actual Collection",
        "Modeled Collection",
        "Forgone Revenue",
        "Modeled Rate (%)",
        "Rate Difference (%)",
    ]
    rate_table = rate_table[
        [
            "Fiscal Year",
            "Modeled Rate (%)",
            "Actual Effective Rate (%)",
            "Rate Difference (%)",
            "Actual Collection",
            "Modeled Collection",
            "Forgone Revenue",
        ]
    ].sort_values("Fiscal Year", ascending=False)

    st.dataframe(
        rate_table.style.format(
            {
                "Modeled Rate (%)": "{:.2f}%",
                "Actual Effective Rate (%)": "{:.2f}%",
                "Rate Difference (%)": "{:.2f}%",
                "Actual Collection": "${:,.0f}",
                "Modeled Collection": "${:,.0f}",
                "Forgone Revenue": "${:,.0f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download Bar Chart Data",
        d2[["local_government", "fy", "actual_rate", "fy_total", "modeled_collection", "forgone_revenue"]]
        .to_csv(index=False)
        .encode("utf-8"),
        file_name=f"{muni_bar}_lgdf_bar_data.csv",
        mime="text/csv",
    )


# ===================================================
# LINE CHART TAB
# ===================================================
with tab_chart:
    col_muni, col_years = st.columns([1, 2])
    with col_muni:
        muni_line = st.selectbox("Select Municipality", municipalities, key="muni_line")
    with col_years:
        year_range_line = st.slider(
            "Select Year Range",
            min_year,
            max_year,
            (min_year, max_year),
            key="yr_line",
        )

    d = filter_data(df, muni_line, year_range_line)

    fig_line = go.Figure()

    fig_line.add_trace(
        go.Scatter(
            x=d["fy"],
            y=d["fy_total"],
            mode="lines+markers",
            name="Actual Collection",
            line=dict(color="#7cb342", width=2),
            marker=dict(size=8),
            hovertemplate="FY %{x}<br>Actual: $%{y:,.0f}<extra></extra>",
        )
    )

    fig_line.add_trace(
        go.Scatter(
            x=d["fy"],
            y=d["modeled_collection"],
            mode="lines+markers",
            name=f"Modeled Collection ({modeled_rate:.1f}%)",
            line=dict(color="#1565c0", width=2, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="FY %{x}<br>Modeled: $%{y:,.0f}<extra></extra>",
        )
    )

    fig_line.update_layout(
        title=f"{muni_line} — Actual vs Modeled LGDF Collection",
        xaxis_title="Fiscal Year",
        yaxis_title="Collection ($)",
        yaxis_tickformat=",.0f",
        xaxis_dtick=1,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode="x unified",
    )

    st.plotly_chart(fig_line, use_container_width=True)

    st.subheader("Forgone Revenue Impact")
    col1, col2, col3, col4 = st.columns(4)
    sorted_d = d.sort_values("fy", ascending=False)

    with col1:
        latest_forgone = sorted_d["forgone_revenue"].iloc[0] if len(sorted_d) > 0 else 0
        st.metric("1-Year Impact", f"${latest_forgone:,.0f}")
    with col2:
        three_yr = sorted_d.head(3)["forgone_revenue"].sum() if len(sorted_d) >= 3 else sorted_d["forgone_revenue"].sum()
        st.metric("3-Year Impact", f"${three_yr:,.0f}")
    with col3:
        five_yr = sorted_d.head(5)["forgone_revenue"].sum() if len(sorted_d) >= 5 else sorted_d["forgone_revenue"].sum()
        st.metric("5-Year Impact", f"${five_yr:,.0f}")
    with col4:
        total_forgone = d["forgone_revenue"].sum()
        st.metric("Total Impact", f"${total_forgone:,.0f}")

    st.download_button(
        "Download Chart Data",
        d[["local_government", "fy", "fy_total", "actual_rate", "modeled_collection", "forgone_revenue"]]
        .to_csv(index=False)
        .encode("utf-8"),
        file_name=f"{muni_line}_lgdf_line_data.csv",
        mime="text/csv",
    )


# ===================================================
# TOP MUNICIPALITIES TAB
# ===================================================
with tab_top:
    st.subheader("Top Municipalities by Total Forgone Revenue")

    top_col1, top_col2 = st.columns([1, 2])
    with top_col1:
        top_n = st.selectbox(
            "Show Top",
            [10, 25, 50, 100, 250],
            index=1,
            key="top_n",
        )
    with top_col2:
        year_range_top = st.slider(
            "Select Year Range",
            min_year,
            max_year,
            (min_year, max_year),
            key="yr_top",
        )

    filtered_top = df[df["fy"].between(year_range_top[0], year_range_top[1])]

    muni_totals = filtered_top.groupby("local_government", as_index=False).agg(
        total_actual=("fy_total", "sum"),
        total_modeled=("modeled_collection", "sum"),
        total_forgone=("forgone_revenue", "sum"),
    ).sort_values("total_forgone", ascending=False)

    grand_total = muni_totals["total_forgone"].sum()
    grand_actual = muni_totals["total_actual"].sum()
    grand_modeled = muni_totals["total_modeled"].sum()

    gc1, gc2, gc3 = st.columns(3)
    with gc1:
        st.metric("Grand Total Actual", f"${grand_actual:,.0f}")
    with gc2:
        st.metric("Grand Total Modeled", f"${grand_modeled:,.0f}")
    with gc3:
        st.metric("Grand Total Forgone Revenue", f"${grand_total:,.0f}")

    top_munis = muni_totals.head(top_n)

    # Horizontal bar chart — easier to read municipality names
    fig_top = go.Figure()

    fig_top.add_trace(
        go.Bar(
            y=top_munis["local_government"].iloc[::-1],
            x=top_munis["total_actual"].iloc[::-1],
            name="Actual Collection",
            orientation="h",
            marker_color="rgba(124, 179, 66, 0.5)",
            hovertemplate="%{y}<br>Actual: $%{x:,.0f}<extra></extra>",
        )
    )

    fig_top.add_trace(
        go.Bar(
            y=top_munis["local_government"].iloc[::-1],
            x=top_munis["total_forgone"].iloc[::-1],
            name="Forgone Revenue",
            orientation="h",
            marker_color="rgba(76, 175, 80, 0.9)",
            hovertemplate="%{y}<br>Forgone: $%{x:,.0f}<extra></extra>",
        )
    )

    chart_height = max(500, top_n * 22)

    fig_top.update_layout(
        barmode="stack",
        title=f"Top {top_n} Municipalities — Total Forgone Revenue ({year_range_top[0]}–{year_range_top[1]})",
        xaxis_title="Total Collection ($)",
        xaxis_tickformat=",.0f",
        yaxis_title="",
        height=chart_height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=200),
    )

    st.plotly_chart(fig_top, use_container_width=True)

    # Full ranking table
    st.subheader(f"Top {top_n} — Detailed Ranking")
    display_top = top_munis.copy()
    display_top.insert(0, "Rank", range(1, len(display_top) + 1))
    display_top.columns = [
        "Rank",
        "Municipality",
        "Total Actual Collection",
        "Total Modeled Collection",
        "Total Forgone Revenue",
    ]

    st.dataframe(
        display_top.style.format(
            {
                "Total Actual Collection": "${:,.0f}",
                "Total Modeled Collection": "${:,.0f}",
                "Total Forgone Revenue": "${:,.0f}",
            }
        ),
        use_container_width=True,
        height=min(650, top_n * 38 + 50),
    )

    st.download_button(
        f"Download Top {top_n} Municipalities",
        muni_totals.to_csv(index=False).encode("utf-8"),
        file_name=f"top_municipalities_forgone_revenue_{year_range_top[0]}_{year_range_top[1]}.csv",
        mime="text/csv",
    )


# ===================================================
# TABLE TAB
# ===================================================
with tab_table:
    years = sorted(df["fy"].unique())
    year = st.selectbox("Select Fiscal Year", years, index=len(years) - 1)

    name_filter = st.text_input("Filter Municipality Name (contains)")

    t = df[df["fy"] == year][
        ["local_government", "tax", "fy_total", "actual_rate", "modeled_collection", "forgone_revenue"]
    ].copy()

    if name_filter:
        t = t[t["local_government"].str.contains(name_filter, case=False)]

    t = t.sort_values("forgone_revenue", ascending=False)
    t["fy_total"] = t["fy_total"].round(0)
    t["modeled_collection"] = t["modeled_collection"].round(0)
    t["forgone_revenue"] = t["forgone_revenue"].round(0)

    t.columns = [
        "Local Government",
        "Tax",
        "Actual Collection",
        "Actual Rate (%)",
        f"Modeled Collection ({modeled_rate:.1f}%)",
        "Forgone Revenue",
    ]

    st.dataframe(t, use_container_width=True, height=650)

    st.download_button(
        f"Download FY{year} Table",
        t.to_csv(index=False).encode("utf-8"),
        file_name=f"income_tax_LGDF_FY{year}.csv",
        mime="text/csv",
    )


# ===================================================
# SOURCE / NOTES
# ===================================================
st.markdown("---")
st.subheader("Source & Notes")
st.markdown(
    """
    **Data Source:** Illinois Department of Revenue — *Income Tax, Local Use Tax, and Cannabis Use Tax Disbursements*
    ([tax.illinois.gov/localgovernments/disbursements/incomeanduse.html](https://tax.illinois.gov/localgovernments/disbursements/incomeanduse.html))

    **Methodology:** Modeled collections are calculated by scaling actual disbursements using the ratio of the
    modeled effective rate to the actual effective LGDF rate for each fiscal year:

    *Modeled Collection = Actual Collection x (Modeled Rate / Actual Effective Rate)*

    **Forgone Revenue** represents the difference between modeled and actual collections, indicating revenue
    municipalities would have received under the modeled LGDF rate.
    """
)
