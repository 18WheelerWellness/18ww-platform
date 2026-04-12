import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from io_layer.google_company_store import load_company_rows_from_shared_tab


def _safe_str(val):
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def _to_float(val):
    try:
        text = _safe_str(val).replace("$", "").replace(",", "").replace("%", "")
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def _fmt_money(val):
    if val is None or pd.isna(val):
        return "-"
    return f"${val:,.0f}"


def _fmt_num(val, digits=1):
    if val is None or pd.isna(val):
        return "-"
    if float(val).is_integer():
        return f"{int(val)}"
    return f"{val:.{digits}f}"


def _find_col(df: pd.DataFrame, candidates):
    if df.empty:
        return None
    lowered = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lowered:
            return lowered[cand.lower()]
    return None


def _normalize_claims_df(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    needed = [
        "company_name",
        "claim_number",
        "driver_name",
        "date_of_injury",
        "terminal",
        "cost_savings_by_claim",
        "cost_per_day",
        "actual_rtw_days",
        "company_avg_days_out",
        "lag_days",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    if company_name and company_name != "ALL" and "company_name" in df.columns:
        df["company_name"] = company_name

    for col in needed:
        df[col] = df[col].apply(_safe_str)

    return df


def _load_cost_inputs(company_name: str):
    emod_df = load_company_rows_from_shared_tab(company_name, "emod_inputs")
    settings_df = load_company_rows_from_shared_tab(company_name, "company_settings")
    source_df = emod_df if not emod_df.empty else settings_df

    if source_df.empty:
        return {
            "source": None,
            "total_wc_cost": None,
            "fte_count": None,
            "man_hours": None,
            "program_cost": None,
        }

    row = source_df.iloc[0]

    cost_col = _find_col(source_df, [
        "total_wc_cost",
        "incurred_losses",
        "premium_paid",
        "current_premium",
        "manual_premium",
        "wc_cost",
        "total_claim_cost",
    ])
    fte_col = _find_col(source_df, [
        "fte_count",
        "number_of_employees",
        "employees",
        "employee_count",
        "full_time_equivalent",
        "number_of_drivers",
        "driver_count",
        "drivers",
    ])
    man_hours_col = _find_col(source_df, [
        "man_hours",
        "annual_man_hours",
        "total_man_hours",
        "hours_worked",
    ])
    program_cost_col = _find_col(source_df, [
        "program_cost",
        "annual_program_cost",
        "implementation_cost",
        "cost_of_program",
    ])

    return {
        "source": "emod_inputs" if not emod_df.empty else "company_settings",
        "total_wc_cost": _to_float(row.get(cost_col, "")) if cost_col else None,
        "fte_count": _to_float(row.get(fte_col, "")) if fte_col else None,
        "man_hours": _to_float(row.get(man_hours_col, "")) if man_hours_col else None,
        "program_cost": _to_float(row.get(program_cost_col, "")) if program_cost_col else None,
    }


def _derive_fte_count(fte_count, man_hours):
    if fte_count not in [None, 0]:
        return fte_count
    if man_hours not in [None, 0]:
        return man_hours / 2000.0
    return None


def _period_rollup(df: pd.DataFrame, period_col: str, label_name: str, fte_count):
    if df.empty or fte_count in [None, 0]:
        return pd.DataFrame()

    working = df.copy()
    working = working[working[period_col].astype(str) != "NaT"]
    if working.empty:
        return pd.DataFrame()

    grouped = (
        working.groupby(period_col, dropna=False)
        .agg(
            Claims=("claim_number", "count"),
            Total_Savings=("cost_savings_num", "sum"),
        )
        .reset_index()
        .rename(columns={period_col: label_name})
        .sort_values(label_name)
    )
    grouped["Savings per FTE"] = grouped["Total_Savings"] / fte_count
    return grouped


def _show_chart(compare_df: pd.DataFrame, label_col: str, value_col: str, title: str):
    if compare_df.empty:
        st.info("No data available.")
        return

    chart_df = compare_df[[label_col, value_col]].copy()
    chart_df[value_col] = chart_df[value_col].apply(_to_float)
    chart_df = chart_df.dropna(subset=[value_col])

    if chart_df.empty:
        st.info("No data available.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(chart_df[label_col].astype(str), chart_df[value_col])
    ax.set_ylabel("Dollars")
    ax.set_title(title)
    plt.xticks(rotation=25, ha="right")
    st.pyplot(fig)


def render_cost_per_fte_page():
    st.title("Cost per FTE")
    st.caption("True Cost per FTE is total workers' comp cost divided by FTEs. This page adds the 18WW savings overlay, adjusted cost per FTE, and cost-if-we-hadn't-improved story.")

    company_name = st.session_state.get("company_name", "")
    claims_df = load_company_rows_from_shared_tab(company_name, "claims")
    claims_df = _normalize_claims_df(claims_df, company_name)

    inputs = _load_cost_inputs(company_name)
    total_wc_cost = inputs["total_wc_cost"]
    fte_count = _derive_fte_count(inputs["fte_count"], inputs["man_hours"])
    program_cost = inputs["program_cost"]

    if claims_df.empty:
        claims_df = pd.DataFrame(columns=["claim_number", "date_of_injury", "cost_savings_by_claim", "lag_days", "actual_rtw_days"])

    claims_df = claims_df.copy()
    claims_df["cost_savings_num"] = claims_df["cost_savings_by_claim"].apply(_to_float)
    claims_df["lag_days_num"] = claims_df["lag_days"].apply(_to_float)
    claims_df["actual_rtw_days_num"] = claims_df["actual_rtw_days"].apply(_to_float)
    claims_df["date_of_injury_dt"] = pd.to_datetime(claims_df["date_of_injury"], errors="coerce")
    claims_df["month"] = claims_df["date_of_injury_dt"].dt.to_period("M").astype(str)
    claims_df["quarter"] = claims_df["date_of_injury_dt"].dt.to_period("Q").astype(str)
    claims_df["year"] = claims_df["date_of_injury_dt"].dt.year.astype("Int64").astype(str)

    total_savings = claims_df["cost_savings_num"].dropna().sum() if not claims_df.empty else 0
    total_claims = int(claims_df["claim_number"].astype(str).str.strip().ne("").sum()) if not claims_df.empty else 0
    claims_with_savings = int(claims_df["cost_savings_num"].notna().sum()) if not claims_df.empty else 0
    avg_lag = claims_df["lag_days_num"].dropna().mean() if not claims_df.empty else None
    avg_rtw = claims_df["actual_rtw_days_num"].dropna().mean() if not claims_df.empty else None

    true_cost_per_fte = None
    adjusted_wc_cost = None
    adjusted_cost_per_fte = None
    savings_per_fte = None
    cost_if_no_improvement = None
    cost_if_no_improvement_per_fte = None
    roi = None

    if total_wc_cost is not None:
        cost_if_no_improvement = total_wc_cost + total_savings
        adjusted_wc_cost = max(total_wc_cost - total_savings, 0)

    if total_wc_cost is not None and fte_count not in [None, 0]:
        true_cost_per_fte = total_wc_cost / fte_count
        adjusted_cost_per_fte = adjusted_wc_cost / fte_count if adjusted_wc_cost is not None else None
        savings_per_fte = total_savings / fte_count
        cost_if_no_improvement_per_fte = cost_if_no_improvement / fte_count if cost_if_no_improvement is not None else None

    if program_cost not in [None, 0]:
        roi = ((total_savings - program_cost) / program_cost) * 100

    st.subheader("Headline Metrics")
    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Reported WC Cost", _fmt_money(total_wc_cost))
    top2.metric("FTE Count", _fmt_num(fte_count, 1))
    top3.metric("True Cost per FTE", _fmt_money(true_cost_per_fte))
    top4.metric("Savings per FTE", _fmt_money(savings_per_fte))

    mid1, mid2, mid3, mid4 = st.columns(4)
    mid1.metric("Adjusted WC Cost", _fmt_money(adjusted_wc_cost))
    mid2.metric("Adjusted Cost per FTE", _fmt_money(adjusted_cost_per_fte))
    mid3.metric("Cost if We Hadn't Improved", _fmt_money(cost_if_no_improvement))
    mid4.metric("Cost/FTE If We Hadn't Improved", _fmt_money(cost_if_no_improvement_per_fte))

    low1, low2, low3, low4 = st.columns(4)
    low1.metric("Total Claims", total_claims)
    low2.metric("Claims With Savings", claims_with_savings)
    low3.metric("Avg Lag Time", _fmt_num(avg_lag, 1))
    low4.metric("Avg Actual RTW Days", _fmt_num(avg_rtw, 1))

    if roi is not None:
        st.metric("ROI", f"{roi:.1f}%")

    st.subheader("Cost per FTE Story")
    story_rows = [
        ["Reported WC Cost", _fmt_money(total_wc_cost)],
        ["Total Claim-Level Savings", _fmt_money(total_savings)],
        ["Adjusted WC Cost", _fmt_money(adjusted_wc_cost)],
        ["FTE Count", _fmt_num(fte_count, 1)],
        ["True Cost per FTE", _fmt_money(true_cost_per_fte)],
        ["Adjusted Cost per FTE", _fmt_money(adjusted_cost_per_fte)],
        ["Savings per FTE", _fmt_money(savings_per_fte)],
        ["Cost if We Hadn't Improved", _fmt_money(cost_if_no_improvement)],
        ["Cost/FTE If We Hadn't Improved", _fmt_money(cost_if_no_improvement_per_fte)],
        ["Program Cost", _fmt_money(program_cost)],
        ["ROI", "-" if roi is None else f"{roi:.1f}%"],
        ["Input Source", inputs["source"] or "-"],
    ]
    story_df = pd.DataFrame(story_rows, columns=["Metric", "Value"])
    st.dataframe(story_df, use_container_width=True, hide_index=True)

    st.subheader("Cost per FTE Comparison")
    compare_rows = [
        ["Current Reported Cost/FTE", true_cost_per_fte],
        ["Adjusted Cost/FTE", adjusted_cost_per_fte],
        ["No-Improvement Cost/FTE", cost_if_no_improvement_per_fte],
    ]
    compare_df = pd.DataFrame(compare_rows, columns=["Scenario", "Amount"])
    _show_chart(compare_df, "Scenario", "Amount", "Cost per FTE Comparison")

    st.subheader("Savings per FTE by Period")
    monthly = _period_rollup(claims_df, "month", "Month", fte_count)
    quarterly = _period_rollup(claims_df, "quarter", "Quarter", fte_count)
    yearly = _period_rollup(claims_df, "year", "Year", fte_count)

    if monthly.empty and quarterly.empty and yearly.empty:
        st.info("Add claims with dates and add FTE count or man-hours in emod_inputs or company_settings to unlock monthly, quarterly, and yearly Savings per FTE.")
    else:
        st.markdown("**Monthly**")
        monthly_display = monthly.copy()
        if not monthly_display.empty:
            monthly_display["Total_Savings"] = monthly_display["Total_Savings"].apply(_fmt_money)
            monthly_display["Savings per FTE"] = monthly_display["Savings per FTE"].apply(_fmt_money)
            monthly_display = monthly_display.rename(columns={"Total_Savings": "Total Savings"})
            st.dataframe(monthly_display, use_container_width=True, hide_index=True)
            _show_chart(monthly.rename(columns={"Savings per FTE": "Savings per FTE"}), "Month", "Savings per FTE", "Savings per FTE by Month")

        st.markdown("**Quarterly**")
        quarterly_display = quarterly.copy()
        if not quarterly_display.empty:
            quarterly_display["Total_Savings"] = quarterly_display["Total_Savings"].apply(_fmt_money)
            quarterly_display["Savings per FTE"] = quarterly_display["Savings per FTE"].apply(_fmt_money)
            quarterly_display = quarterly_display.rename(columns={"Total_Savings": "Total Savings"})
            st.dataframe(quarterly_display, use_container_width=True, hide_index=True)
            _show_chart(quarterly.rename(columns={"Savings per FTE": "Savings per FTE"}), "Quarter", "Savings per FTE", "Savings per FTE by Quarter")

        st.markdown("**Yearly**")
        yearly_display = yearly.copy()
        if not yearly_display.empty:
            yearly_display["Total_Savings"] = yearly_display["Total_Savings"].apply(_fmt_money)
            yearly_display["Savings per FTE"] = yearly_display["Savings per FTE"].apply(_fmt_money)
            yearly_display = yearly_display.rename(columns={"Total_Savings": "Total Savings"})
            st.dataframe(yearly_display, use_container_width=True, hide_index=True)
            _show_chart(yearly.rename(columns={"Savings per FTE": "Savings per FTE"}), "Year", "Savings per FTE", "Savings per FTE by Year")

    st.subheader("What This Means")
    st.markdown(
        """
- **True Cost per FTE** shows what workers' comp is costing per employee today.
- **Adjusted Cost per FTE** shows what that cost looks like after the savings your system created.
- **Cost if We Hadn't Improved** shows the bigger cost you likely would be carrying without the intervention.
- **Savings per FTE** is the executive-friendly story number because it shows how much value was created per employee.
"""
    )

    st.success("This upgraded page separates true cost from savings impact, so it matches the financial logic better and tells the before / after story more clearly.")
