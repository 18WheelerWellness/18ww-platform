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


def _to_datetime(val):
    return pd.to_datetime(_safe_str(val), errors="coerce")


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


def _fmt_pct(val):
    if val is None or pd.isna(val):
        return "-"
    return f"{val:.1f}%"


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
        "claim_stage",
        "actual_rtw_days",
        "cost_savings_by_claim",
        "injury_area",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    if company_name and company_name != "ALL" and "company_name" in df.columns:
        df["company_name"] = company_name

    for col in needed:
        df[col] = df[col].apply(_safe_str)

    return df


def _rtw_bucket(days):
    if days is None or pd.isna(days):
        return "Unknown"
    if days <= 3:
        return "0-3 Days"
    if days <= 7:
        return "4-7 Days"
    if days <= 14:
        return "8-14 Days"
    return "15+ Days"


def _build_pdf(company_name, summary_df, detail_df, monthly_df):
    styles = getSampleStyleSheet()
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
    elements = []

    elements.append(Paragraph("18WW RTW Ratio Report", styles["Title"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Company: {_safe_str(company_name) or 'N/A'}", styles["Normal"]))
    elements.append(Spacer(1, 12))

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

    add_table("RTW Ratio Summary", summary_df)
    add_table("Monthly RTW Trend", monthly_df)
    add_table("Claim-Level RTW Detail", detail_df)

    doc.build(elements)
    return tmp_file.name


def render_rtw_ratio_page():
    st.title("RTW Ratio")
    st.caption("RTW Ratio is built from claim-level actual RTW days in Claims. It shows how quickly employees are getting back, where the wins are, and where the delays are.")

    company_name = st.session_state.get("company_name", "")
    claims_df = load_company_rows_from_shared_tab(company_name, "claims")
    claims_df = _normalize_claims_df(claims_df, company_name)

    if claims_df.empty:
        st.warning("No claims data found yet.")
        return

    df = claims_df.copy()
    df["actual_rtw_days_num"] = df["actual_rtw_days"].apply(_to_float)
    df["cost_savings_num"] = df["cost_savings_by_claim"].apply(_to_float)
    df["date_of_injury_dt"] = pd.to_datetime(df["date_of_injury"], errors="coerce")
    df["month"] = df["date_of_injury_dt"].dt.to_period("M").astype(str)
    df["rtw_bucket"] = df["actual_rtw_days_num"].apply(_rtw_bucket)

    valid = df["actual_rtw_days_num"].dropna()
    total_claims = int(df["claim_number"].astype(str).str.strip().ne("").sum())
    claims_with_rtw = int(valid.shape[0])
    avg_rtw = valid.mean() if not valid.empty else None
    best_rtw = valid.min() if not valid.empty else None
    worst_rtw = valid.max() if not valid.empty else None
    pct_3 = valid.le(3).mean() * 100 if not valid.empty else None
    pct_7 = valid.le(7).mean() * 100 if not valid.empty else None
    pct_14 = valid.le(14).mean() * 100 if not valid.empty else None
    total_savings = df["cost_savings_num"].dropna().sum()
    avg_savings = df["cost_savings_num"].dropna().mean()

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("RTW Ratio ≤ 3 Days", _fmt_pct(pct_3))
    top2.metric("RTW Ratio ≤ 7 Days", _fmt_pct(pct_7))
    top3.metric("RTW Ratio ≤ 14 Days", _fmt_pct(pct_14))
    top4.metric("Claims With RTW Data", claims_with_rtw)

    mid1, mid2, mid3, mid4 = st.columns(4)
    mid1.metric("Average RTW Days", _fmt_num(avg_rtw, 1))
    mid2.metric("Best RTW", _fmt_num(best_rtw, 1))
    mid3.metric("Worst RTW", _fmt_num(worst_rtw, 1))
    mid4.metric("Total Claims", total_claims)

    low1, low2 = st.columns(2)
    low1.metric("Total Savings on RTW Claims", _fmt_money(total_savings))
    low2.metric("Avg Savings per RTW Claim", _fmt_money(avg_savings))

    st.subheader("RTW Distribution")
    bucket_order = ["0-3 Days", "4-7 Days", "8-14 Days", "15+ Days", "Unknown"]
    bucket_counts = (
        df["rtw_bucket"]
        .value_counts()
        .reindex(bucket_order, fill_value=0)
        .reset_index()
    )
    bucket_counts.columns = ["Bucket", "Claims"]
    st.dataframe(bucket_counts, use_container_width=True, hide_index=True)

    if bucket_counts["Claims"].sum() > 0:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(bucket_counts["Bucket"], bucket_counts["Claims"])
        ax.set_ylabel("Claims")
        ax.set_title("RTW Day Distribution")
        plt.xticks(rotation=20, ha="right")
        st.pyplot(fig)

    st.subheader("Monthly RTW Trend")
    monthly = (
        df[df["month"] != "NaT"]
        .groupby("month", dropna=False)
        .agg(
            Claims=("claim_number", "count"),
            Avg_RTW=("actual_rtw_days_num", "mean"),
            RTW_3=("actual_rtw_days_num", lambda s: s.dropna().le(3).mean() * 100 if s.dropna().shape[0] else None),
            RTW_7=("actual_rtw_days_num", lambda s: s.dropna().le(7).mean() * 100 if s.dropna().shape[0] else None),
            Savings=("cost_savings_num", "sum"),
        )
        .reset_index()
        .rename(columns={"month": "Month"})
        .sort_values("Month")
    )
    monthly_display = monthly.copy()
    monthly_display["Avg_RTW"] = monthly_display["Avg_RTW"].apply(lambda x: _fmt_num(x, 1))
    monthly_display["RTW_3"] = monthly_display["RTW_3"].apply(_fmt_pct)
    monthly_display["RTW_7"] = monthly_display["RTW_7"].apply(_fmt_pct)
    monthly_display["Savings"] = monthly_display["Savings"].apply(_fmt_money)
    monthly_display = monthly_display.rename(columns={
        "Avg_RTW": "Avg RTW Days",
        "RTW_3": "% ≤ 3 Days",
        "RTW_7": "% ≤ 7 Days",
        "Savings": "Savings",
    })
    st.dataframe(monthly_display, use_container_width=True, hide_index=True)

    if not monthly.empty:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(monthly["Month"].astype(str), monthly["Avg_RTW"], marker="o")
        ax.set_title("Average RTW Days by Month")
        ax.set_ylabel("Days")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig)

    st.subheader("Claim-Level RTW Detail")
    detail = df[[
        "claim_number",
        "driver_name",
        "terminal",
        "injury_area",
        "date_of_injury",
        "actual_rtw_days_num",
        "rtw_bucket",
        "cost_savings_num",
        "claim_stage",
    ]].copy()
    detail = detail.rename(columns={
        "claim_number": "Claim Number",
        "driver_name": "Driver",
        "terminal": "Terminal",
        "injury_area": "Injury Area",
        "date_of_injury": "Date of Injury",
        "actual_rtw_days_num": "Actual RTW Days",
        "rtw_bucket": "RTW Bucket",
        "cost_savings_num": "Savings",
        "claim_stage": "Claim Stage",
    })
    detail["Actual RTW Days"] = detail["Actual RTW Days"].apply(lambda x: _fmt_num(x, 1))
    detail["Savings"] = detail["Savings"].apply(_fmt_money)
    st.dataframe(detail, use_container_width=True, hide_index=True)

    st.subheader("Summary")
    summary_rows = [
        ["RTW Ratio ≤ 3 Days", _fmt_pct(pct_3)],
        ["RTW Ratio ≤ 7 Days", _fmt_pct(pct_7)],
        ["RTW Ratio ≤ 14 Days", _fmt_pct(pct_14)],
        ["Average RTW Days", _fmt_num(avg_rtw, 1)],
        ["Best RTW", _fmt_num(best_rtw, 1)],
        ["Worst RTW", _fmt_num(worst_rtw, 1)],
        ["Total Savings on RTW Claims", _fmt_money(total_savings)],
        ["Avg Savings per RTW Claim", _fmt_money(avg_savings)],
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.subheader("Export")
    if st.button("Export RTW Ratio PDF"):
        pdf_path = _build_pdf(company_name, summary_df, detail, monthly_display)
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download RTW Ratio PDF",
                f,
                file_name="18WW_RTW_Ratio_Report.pdf",
                mime="application/pdf",
            )

    st.success("This page shows how quickly employees are getting back to work and ties that speed to real savings.")
