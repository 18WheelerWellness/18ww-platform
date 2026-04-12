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
        "date_of_injury",
        "terminal",
        "injury_area",
        "claim_stage",
        "cost_savings_by_claim",
        "company_avg_days_out",
        "actual_rtw_days",
        "cost_per_day",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    if company_name and company_name != "ALL" and "company_name" in df.columns:
        df["company_name"] = company_name

    for col in needed:
        df[col] = df[col].apply(_safe_str)

    return df


def _load_financial_inputs(company_name: str):
    fin_df = load_company_rows_from_shared_tab(company_name, "financial_inputs")
    emod_df = load_company_rows_from_shared_tab(company_name, "emod_inputs")
    settings_df = load_company_rows_from_shared_tab(company_name, "company_settings")
    source_df = fin_df if not fin_df.empty else (emod_df if not emod_df.empty else settings_df)

    result = {
        "source": None,
        "profit_margin_percent": None,
        "avg_sale_value": None,
        "program_cost": None,
    }

    if source_df.empty:
        return result

    row = source_df.iloc[0]
    lowered = {str(c).strip().lower(): c for c in source_df.columns}

    def find(candidates):
        for cand in candidates:
            if cand.lower() in lowered:
                return lowered[cand.lower()]
        return None

    margin_col = find([
        "profit_margin_percent",
        "profit_margin",
        "net_margin_percent",
        "margin_percent",
        "gross_margin_percent",
    ])
    sale_col = find([
        "avg_sale_value",
        "average_sale_value",
        "average_sale",
        "avg_revenue_per_sale",
        "revenue_per_sale",
        "sale_value",
    ])
    program_cost_col = find([
        "program_cost",
        "annual_program_cost",
        "implementation_cost",
        "cost_of_program",
    ])

    result["source"] = "financial_inputs" if not fin_df.empty else ("emod_inputs" if not emod_df.empty else "company_settings")
    result["profit_margin_percent"] = _to_float(row.get(margin_col, "")) if margin_col else None
    result["avg_sale_value"] = _to_float(row.get(sale_col, "")) if sale_col else None
    result["program_cost"] = _to_float(row.get(program_cost_col, "")) if program_cost_col else None
    return result


def _build_pdf(company_name, summary_df, with_without_df, monthly_df, claim_df):
    styles = getSampleStyleSheet()
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp_file.name, pagesize=letter)
    elements = []

    elements.append(Paragraph("18WW Sales to Pay for Accident Report", styles["Title"]))
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

    add_table("Summary", summary_df)
    add_table("With vs Without RTW", with_without_df)
    add_table("Monthly Rollup", monthly_df)
    add_table("Claim-Level Rollup", claim_df)

    doc.build(elements)
    return tmp_file.name


def render_sales_to_pay_page():
    st.title("Sales to Pay for Accident")
    st.caption("Turns verified claim savings into revenue language and shows the with-vs-without RTW difference using real claim data.")

    company_name = st.session_state.get("company_name", "")
    claims_df = load_company_rows_from_shared_tab(company_name, "claims")
    claims_df = _normalize_claims_df(claims_df, company_name)

    if claims_df.empty:
        st.warning("No claims data found yet.")
        return

    inputs = _load_financial_inputs(company_name)

    df = claims_df.copy()
    df["cost_savings_num"] = df["cost_savings_by_claim"].apply(_to_float)
    df["company_avg_days_out_num"] = df["company_avg_days_out"].apply(_to_float)
    df["actual_rtw_days_num"] = df["actual_rtw_days"].apply(_to_float)
    df["cost_per_day_num"] = df["cost_per_day"].apply(_to_float)
    df["date_of_injury_dt"] = pd.to_datetime(df["date_of_injury"], errors="coerce")
    df["month"] = df["date_of_injury_dt"].dt.to_period("M").astype(str)

    # With vs without RTW core math
    df["without_rtw_cost_num"] = df["company_avg_days_out_num"] * df["cost_per_day_num"]
    df["with_rtw_cost_num"] = df["actual_rtw_days_num"] * df["cost_per_day_num"]

    # prefer saved verified savings if present, otherwise derive it
    derived_savings = (df["without_rtw_cost_num"] - df["with_rtw_cost_num"]).clip(lower=0)
    df["verified_savings_num"] = df["cost_savings_num"].where(df["cost_savings_num"].notna(), derived_savings)

    profit_margin_percent = inputs["profit_margin_percent"]
    avg_sale_value = inputs["avg_sale_value"]
    program_cost = inputs["program_cost"]

    if profit_margin_percent not in [None, 0]:
        margin_decimal = profit_margin_percent / 100.0 if profit_margin_percent > 1 else profit_margin_percent
    else:
        margin_decimal = None

    df["without_rtw_revenue_num"] = df["without_rtw_cost_num"] / margin_decimal if margin_decimal else None
    df["with_rtw_revenue_num"] = df["with_rtw_cost_num"] / margin_decimal if margin_decimal else None
    df["sales_pressure_removed_num"] = df["verified_savings_num"] / margin_decimal if margin_decimal else None

    total_claims = int(df["claim_number"].astype(str).str.strip().ne("").sum())
    total_verified_savings = df["verified_savings_num"].dropna().sum()
    avg_verified_savings = df["verified_savings_num"].dropna().mean()
    total_without_rtw_cost = df["without_rtw_cost_num"].dropna().sum()
    total_with_rtw_cost = df["with_rtw_cost_num"].dropna().sum()
    total_without_rtw_revenue = df["without_rtw_revenue_num"].dropna().sum() if margin_decimal else None
    total_with_rtw_revenue = df["with_rtw_revenue_num"].dropna().sum() if margin_decimal else None
    sales_pressure_removed = df["sales_pressure_removed_num"].dropna().sum() if margin_decimal else None

    sales_to_cover_saved_loss = (sales_pressure_removed / avg_sale_value) if (sales_pressure_removed is not None and avg_sale_value not in [None, 0]) else None
    revenue_needed_to_cover_avg_claim = (avg_verified_savings / margin_decimal) if (avg_verified_savings is not None and margin_decimal) else None
    revenue_needed_to_cover_program = (program_cost / margin_decimal) if (program_cost not in [None] and margin_decimal) else None
    headline_total_improvement = total_verified_savings + (sales_pressure_removed or 0)

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Total Verified Savings", _fmt_money(total_verified_savings))
    top2.metric("Sales Pressure Removed", _fmt_money(sales_pressure_removed))
    top3.metric("Headline Total Improvement", _fmt_money(headline_total_improvement))
    top4.metric("Total Claims", total_claims)

    mid1, mid2, mid3, mid4 = st.columns(4)
    mid1.metric("Avg Savings per Claim", _fmt_money(avg_verified_savings))
    mid2.metric("Profit Margin Used", "-" if profit_margin_percent is None else f"{profit_margin_percent:.1f}%")
    mid3.metric("Avg Sale Value", _fmt_money(avg_sale_value))
    mid4.metric("Sales Needed to Replace Saved Loss", _fmt_num(sales_to_cover_saved_loss, 1))

    low1, low2, low3 = st.columns(3)
    low1.metric("Revenue Needed to Cover Avg Claim", _fmt_money(revenue_needed_to_cover_avg_claim))
    low2.metric("Program Cost", _fmt_money(program_cost))
    low3.metric("Revenue Needed to Cover Program", _fmt_money(revenue_needed_to_cover_program))

    st.subheader("With vs Without RTW")
    with_without_df = pd.DataFrame([
        ["Without RTW", _fmt_money(total_without_rtw_cost), _fmt_money(total_without_rtw_revenue)],
        ["With RTW", _fmt_money(total_with_rtw_cost), _fmt_money(total_with_rtw_revenue)],
        ["Difference", _fmt_money(total_verified_savings), _fmt_money(sales_pressure_removed)],
    ], columns=["Scenario", "Cost", "Revenue Needed"])
    st.dataframe(with_without_df, use_container_width=True, hide_index=True)

    ww_chart = pd.DataFrame({
        "Scenario": ["Without RTW", "With RTW"],
        "Cost": [total_without_rtw_cost or 0, total_with_rtw_cost or 0],
        "Revenue Needed": [total_without_rtw_revenue or 0, total_with_rtw_revenue or 0],
    })

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(ww_chart["Scenario"], ww_chart["Cost"])
    ax.set_ylabel("Dollars")
    ax.set_title("Cost: Without RTW vs With RTW")
    st.pyplot(fig)

    if margin_decimal:
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.bar(ww_chart["Scenario"], ww_chart["Revenue Needed"])
        ax2.set_ylabel("Dollars")
        ax2.set_title("Revenue Needed: Without RTW vs With RTW")
        st.pyplot(fig2)

    st.subheader("Why This Matters")
    st.markdown(
        """
- **Without RTW** shows the likely cost path if the employee stayed out based on the company's average days out.
- **With RTW** shows the actual cost path based on real RTW timing.
- **Difference** is the cost avoided and the revenue burden the company no longer has to chase just to get back to even.
"""
    )

    st.subheader("Monthly Sales Pressure Rollup")
    monthly = (
        df[df["month"] != "NaT"]
        .groupby("month", dropna=False)
        .agg(
            Claims=("claim_number", "count"),
            Without_RTW_Cost=("without_rtw_cost_num", "sum"),
            With_RTW_Cost=("with_rtw_cost_num", "sum"),
            Total_Savings=("verified_savings_num", "sum"),
            Sales_Pressure_Removed=("sales_pressure_removed_num", "sum"),
        )
        .reset_index()
        .rename(columns={"month": "Month"})
        .sort_values("Month")
    )
    monthly["Headline Total Improvement"] = monthly["Total_Savings"] + monthly["Sales_Pressure_Removed"].fillna(0)

    monthly_display = monthly.copy()
    for col in ["Without_RTW_Cost", "With_RTW_Cost", "Total_Savings", "Sales_Pressure_Removed", "Headline Total Improvement"]:
        monthly_display[col] = monthly_display[col].apply(_fmt_money)
    monthly_display = monthly_display.rename(columns={
        "Without_RTW_Cost": "Without RTW Cost",
        "With_RTW_Cost": "With RTW Cost",
        "Total_Savings": "Total Savings",
        "Sales_Pressure_Removed": "Sales Pressure Removed",
    })
    st.dataframe(monthly_display, use_container_width=True, hide_index=True)

    if not monthly.empty and monthly["Sales_Pressure_Removed"].dropna().shape[0] > 0:
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        ax3.plot(monthly["Month"].astype(str), monthly["Sales_Pressure_Removed"], marker="o")
        ax3.set_title("Sales Pressure Removed by Month")
        ax3.set_ylabel("Dollars")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig3)

    st.subheader("Claim-Level With vs Without RTW")
    claim_view = df[[
        "claim_number",
        "driver_name",
        "terminal",
        "injury_area",
        "claim_stage",
        "date_of_injury",
        "company_avg_days_out_num",
        "actual_rtw_days_num",
        "without_rtw_cost_num",
        "with_rtw_cost_num",
        "verified_savings_num",
        "sales_pressure_removed_num",
    ]].copy()

    claim_view = claim_view.rename(columns={
        "claim_number": "Claim Number",
        "driver_name": "Driver",
        "terminal": "Terminal",
        "injury_area": "Injury Area",
        "claim_stage": "Claim Stage",
        "date_of_injury": "Date of Injury",
        "company_avg_days_out_num": "Without RTW Days",
        "actual_rtw_days_num": "With RTW Days",
        "without_rtw_cost_num": "Without RTW Cost",
        "with_rtw_cost_num": "With RTW Cost",
        "verified_savings_num": "Verified Savings",
        "sales_pressure_removed_num": "Sales Pressure Removed",
    })

    for col in ["Without RTW Days", "With RTW Days"]:
        claim_view[col] = claim_view[col].apply(lambda x: _fmt_num(x, 1))
    for col in ["Without RTW Cost", "With RTW Cost", "Verified Savings", "Sales Pressure Removed"]:
        claim_view[col] = claim_view[col].apply(_fmt_money)

    st.dataframe(claim_view, use_container_width=True, hide_index=True)

    st.subheader("Summary")
    summary_rows = [
        ["Total Verified Savings", _fmt_money(total_verified_savings)],
        ["Without RTW Cost", _fmt_money(total_without_rtw_cost)],
        ["With RTW Cost", _fmt_money(total_with_rtw_cost)],
        ["Without RTW Revenue Needed", _fmt_money(total_without_rtw_revenue)],
        ["With RTW Revenue Needed", _fmt_money(total_with_rtw_revenue)],
        ["Sales Pressure Removed", _fmt_money(sales_pressure_removed)],
        ["Headline Total Improvement", _fmt_money(headline_total_improvement)],
        ["Avg Savings per Claim", _fmt_money(avg_verified_savings)],
        ["Profit Margin Used", "-" if profit_margin_percent is None else f"{profit_margin_percent:.1f}%"],
        ["Avg Sale Value", _fmt_money(avg_sale_value)],
        ["Sales Needed to Replace Saved Loss", _fmt_num(sales_to_cover_saved_loss, 1)],
        ["Revenue Needed to Cover Avg Claim", _fmt_money(revenue_needed_to_cover_avg_claim)],
        ["Program Cost", _fmt_money(program_cost)],
        ["Revenue Needed to Cover Program", _fmt_money(revenue_needed_to_cover_program)],
        ["Input Source", inputs["source"] or "-"],
    ]
    summary_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.subheader("Export")
    if st.button("Export Sales to Pay for Accident PDF"):
        pdf_path = _build_pdf(company_name, summary_df, with_without_df, monthly_display, claim_view)
        with open(pdf_path, "rb") as f:
            st.download_button(
                "Download Sales to Pay for Accident PDF",
                f,
                file_name="18WW_Sales_to_Pay_for_Accident_Report.pdf",
                mime="application/pdf",
            )

    st.success("This page now includes with-vs-without RTW so the revenue gap is easier to explain and sell.")
