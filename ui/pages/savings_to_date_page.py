import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
import tempfile

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
    if isinstance(val, float) and not float(val).is_integer():
        return f"{val:.{digits}f}"
    return f"{int(val)}"


def _normalize_claims_df(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    needed = [
        "company_name",
        "claim_number",
        "driver_name",
        "terminal",
        "date_of_injury",
        "injury_area",
        "injury_description",
        "claim_stage",
        "lag_days",
        "actual_rtw_days",
        "cost_savings_by_claim",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    if company_name and company_name != "ALL" and "company_name" in df.columns:
        df["company_name"] = company_name

    for col in needed:
        df[col] = df[col].apply(_safe_str)

    return df


def _get_fee_percent(company_name: str) -> float:
    settings_df = load_company_rows_from_shared_tab(company_name, "company_settings")

    if not settings_df.empty:
        settings_df = settings_df.copy()
        settings_df.columns = [str(c).strip().lower() for c in settings_df.columns]

        if "company_name" in settings_df.columns:
            normalized_target = _safe_str(company_name).lower().replace("_", " ")
            settings_df["company_name_norm"] = (
                settings_df["company_name"]
                .astype(str)
                .str.strip()
                .str.lower()
                .str.replace("_", " ", regex=False)
            )
            match = settings_df[settings_df["company_name_norm"] == normalized_target]
            if not match.empty:
                row = match.iloc[0]
                for fee_col in ["fee_percent", "performance_fee_percent", "18ww_fee_percent", "fee_pct"]:
                    if fee_col in settings_df.columns:
                        val = _to_float(row.get(fee_col, ""))
                        if val is not None:
                            if val > 1:
                                val = val / 100.0
                            if 0 <= val <= 1:
                                return val

    raw = st.session_state.get("fee_percent", 0.15)
    try:
        val = float(raw)
        if val > 1:
            val = val / 100.0
        if 0 <= val <= 1:
            return val
    except Exception:
        pass

    return 0.15


def _format_period_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        return raw_df
    display = raw_df.copy()
    money_cols = [c for c in display.columns if c in ["Total Savings", "18WW Fee", "Fleet Net", "Cumulative Total Savings", "Cumulative Fleet Net", "Cumulative 18WW Fee"]]
    for col in money_cols:
        display[col] = display[col].apply(_fmt_money)
    return display


def _build_pdf(company_name, total_savings, total_fee, total_net, fee_percent, claim_df, monthly_df, quarterly_df, yearly_df):
    styles = getSampleStyleSheet()
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
    elements = []

    elements.append(Paragraph("18WW Savings to Date Report", styles["Title"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Company: {_safe_str(company_name) or 'N/A'}", styles["Normal"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Total Verified Savings to Date: {_fmt_money(total_savings)}", styles["Normal"]))
    elements.append(Paragraph(f"18WW Performance Fee to Date: {_fmt_money(total_fee)}", styles["Normal"]))
    elements.append(Paragraph(f"Fleet Net Savings to Date: {_fmt_money(total_net)}", styles["Normal"]))
    elements.append(Paragraph(f"Fleet Keeps: {(1-fee_percent)*100:.0f}%", styles["Normal"]))
    elements.append(Spacer(1, 14))

    def add_table(title, df):
        elements.append(Paragraph(title, styles["Heading2"]))
        if df is None or df.empty:
            elements.append(Paragraph("No data available.", styles["Normal"]))
            elements.append(Spacer(1, 10))
            return
        table_data = [list(df.columns)] + df.astype(str).values.tolist()
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    add_table("Claims Included", claim_df)
    add_table("Monthly Savings to Date", monthly_df)
    add_table("Quarterly Savings to Date", quarterly_df)
    add_table("Yearly Savings to Date", yearly_df)

    doc.build(elements)
    return tmp_file.name


def _show_line_chart(df: pd.DataFrame, label_col: str, value_col: str, title: str):
    if df.empty:
        st.info("No data available.")
        return
    chart_df = df[[label_col, value_col]].copy()
    chart_df[value_col] = chart_df[value_col].apply(_to_float)
    chart_df = chart_df.dropna(subset=[value_col])
    if chart_df.empty:
        st.info("No data available.")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(chart_df[label_col].astype(str), chart_df[value_col], marker="o")
    ax.set_title(title)
    ax.set_ylabel("Dollars")
    plt.xticks(rotation=45, ha="right")
    st.pyplot(fig)


def render_savings_to_date_page():
    st.title("Savings to Date")
    st.caption("Cumulative savings layer built from claim-level savings truth. This shows what has been saved so far, what the fleet keeps, and what 18WW has earned to date.")

    company_name = st.session_state.get("company_name", "")
    claims_df = load_company_rows_from_shared_tab(company_name, "claims")
    claims_df = _normalize_claims_df(claims_df, company_name)

    if claims_df.empty:
        st.warning("No claims data found yet.")
        return

    df = claims_df.copy()
    df["date_of_injury_dt"] = pd.to_datetime(df["date_of_injury"], errors="coerce")
    df["cost_savings_num"] = df["cost_savings_by_claim"].apply(_to_float)
    df["lag_days_num"] = df["lag_days"].apply(_to_float)
    df["actual_rtw_days_num"] = df["actual_rtw_days"].apply(_to_float)

    fee_percent = _get_fee_percent(company_name)
    df["18ww_fee_num"] = df["cost_savings_num"] * fee_percent
    df["fleet_net_num"] = df["cost_savings_num"] - df["18ww_fee_num"]

    df["month"] = df["date_of_injury_dt"].dt.to_period("M").astype(str)
    df["quarter"] = df["date_of_injury_dt"].dt.to_period("Q").astype(str)
    df["year"] = df["date_of_injury_dt"].dt.year.astype("Int64").astype(str)

    total_claims = int(df["claim_number"].astype(str).str.strip().ne("").sum())
    claims_with_savings = int(df["cost_savings_num"].notna().sum())
    total_savings = df["cost_savings_num"].dropna().sum()
    total_fee = df["18ww_fee_num"].dropna().sum()
    total_net = df["fleet_net_num"].dropna().sum()
    avg_lag = df["lag_days_num"].dropna().mean()
    avg_rtw = df["actual_rtw_days_num"].dropna().mean()

    st.subheader("Savings to Date Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Verified Savings to Date", _fmt_money(total_savings))
    c2.metric("Fleet Net Savings to Date", _fmt_money(total_net))
    c3.metric("18WW Revenue to Date", _fmt_money(total_fee))
    c4.metric("Fleet Keeps", f"{(1-fee_percent)*100:.0f}%")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Claims", total_claims)
    m2.metric("Claims With Savings", claims_with_savings)
    m3.metric("Avg Lag Time", _fmt_num(avg_lag, 1))
    m4.metric("Avg Actual RTW Days", _fmt_num(avg_rtw, 1))

    st.subheader("Cumulative Savings Story")
    fig, ax = plt.subplots()
    labels = ["Savings to Date"]
    fleet_vals = [total_net if pd.notna(total_net) else 0]
    fee_vals = [total_fee if pd.notna(total_fee) else 0]
    ax.bar(labels, fleet_vals, label="Fleet Keeps")
    ax.bar(labels, fee_vals, bottom=fleet_vals, label="18WW Fee")
    ax.set_ylabel("Dollars")
    ax.legend()
    st.pyplot(fig)

    st.subheader("Claims Included in Savings to Date")
    claim_display = df[[
        "claim_number",
        "driver_name",
        "terminal",
        "injury_area",
        "claim_stage",
        "date_of_injury",
        "cost_savings_num",
        "18ww_fee_num",
        "fleet_net_num",
    ]].copy()
    claim_display = claim_display.rename(columns={
        "claim_number": "Claim Number",
        "driver_name": "Driver",
        "terminal": "Terminal",
        "injury_area": "Injury Area",
        "claim_stage": "Claim Stage",
        "date_of_injury": "Date of Injury",
        "cost_savings_num": "Total Savings",
        "18ww_fee_num": "18WW Fee",
        "fleet_net_num": "Fleet Net",
    })
    for col in ["Total Savings", "18WW Fee", "Fleet Net"]:
        claim_display[col] = claim_display[col].apply(_fmt_money)
    claim_display["_sort"] = df["cost_savings_num"]
    claim_display = claim_display.sort_values("_sort", ascending=False, na_position="last").drop(columns=["_sort"])
    st.dataframe(claim_display, use_container_width=True, hide_index=True)

    st.subheader("Monthly Savings to Date")
    monthly = (
        df[df["month"] != "NaT"]
        .groupby("month", dropna=False)
        .agg(
            Claims=("claim_number", "count"),
            **{
                "Total Savings": ("cost_savings_num", "sum"),
                "18WW Fee": ("18ww_fee_num", "sum"),
                "Fleet Net": ("fleet_net_num", "sum"),
            }
        )
        .reset_index()
        .rename(columns={"month": "Month"})
        .sort_values("Month")
    )
    if not monthly.empty:
        monthly["Cumulative Total Savings"] = monthly["Total Savings"].cumsum()
        monthly["Cumulative Fleet Net"] = monthly["Fleet Net"].cumsum()
        monthly["Cumulative 18WW Fee"] = monthly["18WW Fee"].cumsum()
    st.dataframe(_format_period_df(monthly), use_container_width=True, hide_index=True)
    _show_line_chart(monthly, "Month", "Cumulative Fleet Net", "Cumulative Fleet Net Savings by Month")

    st.subheader("Quarterly Savings to Date")
    quarterly = (
        df[df["quarter"] != "NaT"]
        .groupby("quarter", dropna=False)
        .agg(
            Claims=("claim_number", "count"),
            **{
                "Total Savings": ("cost_savings_num", "sum"),
                "18WW Fee": ("18ww_fee_num", "sum"),
                "Fleet Net": ("fleet_net_num", "sum"),
            }
        )
        .reset_index()
        .rename(columns={"quarter": "Quarter"})
        .sort_values("Quarter")
    )
    if not quarterly.empty:
        quarterly["Cumulative Total Savings"] = quarterly["Total Savings"].cumsum()
        quarterly["Cumulative Fleet Net"] = quarterly["Fleet Net"].cumsum()
        quarterly["Cumulative 18WW Fee"] = quarterly["18WW Fee"].cumsum()
    st.dataframe(_format_period_df(quarterly), use_container_width=True, hide_index=True)
    _show_line_chart(quarterly, "Quarter", "Cumulative Fleet Net", "Cumulative Fleet Net Savings by Quarter")

    st.subheader("Yearly Savings to Date")
    yearly = (
        df[(df["year"] != "<NA>") & (df["year"] != "NaT")]
        .groupby("year", dropna=False)
        .agg(
            Claims=("claim_number", "count"),
            **{
                "Total Savings": ("cost_savings_num", "sum"),
                "18WW Fee": ("18ww_fee_num", "sum"),
                "Fleet Net": ("fleet_net_num", "sum"),
            }
        )
        .reset_index()
        .rename(columns={"year": "Year"})
        .sort_values("Year")
    )
    if not yearly.empty:
        yearly["Cumulative Total Savings"] = yearly["Total Savings"].cumsum()
        yearly["Cumulative Fleet Net"] = yearly["Fleet Net"].cumsum()
        yearly["Cumulative 18WW Fee"] = yearly["18WW Fee"].cumsum()
    st.dataframe(_format_period_df(yearly), use_container_width=True, hide_index=True)
    _show_line_chart(yearly, "Year", "Cumulative Fleet Net", "Cumulative Fleet Net Savings by Year")

    st.subheader("Export")
    if st.button("Export Savings to Date PDF"):
        pdf_path = _build_pdf(
            company_name,
            total_savings,
            total_fee,
            total_net,
            fee_percent,
            claim_display,
            _format_period_df(monthly),
            _format_period_df(quarterly),
            _format_period_df(yearly),
        )
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download Savings to Date PDF",
                f,
                file_name="18WW_Savings_to_Date_Report.pdf",
                mime="application/pdf",
            )

    st.success("This page tracks cumulative savings over time using the same claim-level savings truth as the Savings page.")
