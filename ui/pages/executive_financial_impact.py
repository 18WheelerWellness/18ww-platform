
import streamlit as st
import pandas as pd
import tempfile
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

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
        "terminal",
        "date_of_injury",
        "lag_days",
        "actual_rtw_days",
        "cost_savings_by_claim",
        "company_avg_days_out",
        "cost_per_day",
        "claim_stage",
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
        "total_wc_cost": None,
        "fte_count": None,
        "man_hours": None,
    }

    if source_df.empty:
        return result

    row = source_df.iloc[0]
    result["source"] = "financial_inputs" if not fin_df.empty else ("emod_inputs" if not emod_df.empty else "company_settings")

    def pick(cands):
        col = _find_col(source_df, cands)
        return _to_float(row.get(col, "")) if col else None

    result["profit_margin_percent"] = pick(["profit_margin_percent", "profit_margin", "net_margin_percent", "margin_percent"])
    result["avg_sale_value"] = pick(["avg_sale_value", "average_sale_value", "average_sale", "avg_revenue_per_sale", "revenue_per_sale", "sale_value"])
    result["program_cost"] = pick(["program_cost", "annual_program_cost", "implementation_cost", "cost_of_program"])
    result["total_wc_cost"] = pick(["total_wc_cost", "incurred_losses", "premium_paid", "current_premium", "manual_premium", "wc_cost", "total_claim_cost"])
    result["fte_count"] = pick(["fte_count", "number_of_employees", "employees", "employee_count", "full_time_equivalent", "number_of_drivers", "driver_count", "drivers"])
    result["man_hours"] = pick(["man_hours", "annual_man_hours", "total_man_hours", "hours_worked"])
    return result


def _get_fee_percent(company_name: str) -> float:
    settings_df = load_company_rows_from_shared_tab(company_name, "company_settings")

    if not settings_df.empty:
        settings_df = settings_df.copy()
        settings_df.columns = [str(c).strip().lower() for c in settings_df.columns]
        if "company_name" in settings_df.columns:
            normalized_target = _safe_str(company_name).lower().replace("_", " ")
            settings_df["company_name_norm"] = (
                settings_df["company_name"].astype(str).str.strip().str.lower().str.replace("_", " ", regex=False)
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


def _derive_fte_count(fte_count, man_hours):
    if fte_count not in [None, 0]:
        return fte_count
    if man_hours not in [None, 0]:
        return man_hours / 2000.0
    return None



import os
import tempfile
from datetime import datetime
from reportlab.platypus import Image as RLImage
from reportlab.lib.units import inch

PDF_LOGO_PATH = r"/mnt/data/18ww_logo.png"

def _pdf_header_elements(title, company_name, subtitle="Executive report"):
    elements = []
    if os.path.exists(PDF_LOGO_PATH):
        elements.append(RLImage(PDF_LOGO_PATH, width=0.9*inch, height=0.9*inch))
        elements.append(Spacer(1, 6))
    styles = getSampleStyleSheet()
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"Company: {_safe_text(company_name) or 'N/A'}", styles["Normal"]))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d')}", styles["Normal"]))
    elements.append(Paragraph(subtitle, styles["Italic"]))
    elements.append(Spacer(1, 12))
    return elements

def _draw_pdf_footer(canvas, doc, report_name="18WW Report"):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#52606F"))
    canvas.drawString(doc.leftMargin, 20, f"18WW | {report_name}")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 20, f"Page {doc.page}")
    canvas.restoreState()


PDF_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "18ww_logo.png")

def _pdf_header_elements(title, company_name, subtitle="Executive report"):
    styles = getSampleStyleSheet()
    elements = []

    logo_cell = ""
    if os.path.exists(PDF_LOGO_PATH):
        try:
            logo_cell = RLImage(PDF_LOGO_PATH, width=1.0*inch, height=1.0*inch)
        except Exception:
            logo_cell = ""

    title_html = (
        f"<b>{title}</b><br/>"
        f"Company: {_safe_text(company_name) if '_safe_text' in globals() else (_safe_str(company_name) if '_safe_str' in globals() else company_name)}<br/>"
        f"Generated: {datetime.now().strftime('%Y-%m-%d')}<br/>"
        f"<i>{subtitle}</i>"
    )

    header_table = Table(
        [[logo_cell, Paragraph(title_html, styles["Normal"])]],
        colWidths=[1.2*inch, 5.8*inch]
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))
    return elements

def _draw_pdf_footer(canvas, doc, report_name="18WW Report"):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#52606F"))
    canvas.drawString(doc.leftMargin, 20, f"18WW | {report_name}")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 20, f"Page {doc.page}")
    canvas.restoreState()

def _build_pdf(title, company_name, headline_df, detail_df):
    styles = getSampleStyleSheet()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=letter)
    elements = _pdf_header_elements("Executive Business Impact", company_name, "Executive business impact report")

    def add_table(title_text, df):
        elements.append(Paragraph(title_text, styles["Heading2"]))
        if df is None or df.empty:
            elements.append(Paragraph("No data available.", styles["Normal"]))
            elements.append(Spacer(1, 10))
            return
        table_data = [list(df.columns)] + df.astype(str).values.tolist()
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(table)
    
    add_table("Headline Metrics", headline_df)
    add_table("Detail Rollup", detail_df)

    doc.build(elements, onFirstPage=lambda c,d: _draw_pdf_footer(c,d,"Executive Business Impact"), onLaterPages=lambda c,d: _draw_pdf_footer(c,d,"Executive Business Impact"))
    return tmp.name


def _display_rollup(df_in):
    out = df_in.copy()
    if out.empty:
        return out
    for col in ["Total Savings", "18WW Fee", "Fleet Net", "Sales Pressure Removed"]:
        if col in out.columns:
            out[col] = out[col].apply(_fmt_money)
    for col in ["Avg Lag", "Avg RTW Days"]:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: _fmt_num(x, 1))
    return out


def render_executive_financial_impact():
    st.title("Executive Business Impact")
    st.caption("Executive business impact with cleaner monthly, quarterly, and yearly rollups plus separate PDF exports.")

    company_name = st.session_state.get("company_name", "")
    claims_df = load_company_rows_from_shared_tab(company_name, "claims")
    claims_df = _normalize_claims_df(claims_df, company_name)
    fin = _load_financial_inputs(company_name)
    fee_percent = _get_fee_percent(company_name)

    if claims_df.empty and fin["total_wc_cost"] is None:
        st.warning("No claims or financial inputs found yet.")
        return

    df = claims_df.copy()
    if not df.empty:
        df["lag_days_num"] = df["lag_days"].apply(_to_float)
        df["actual_rtw_days_num"] = df["actual_rtw_days"].apply(_to_float)
        df["cost_savings_num"] = df["cost_savings_by_claim"].apply(_to_float)
        df["company_avg_days_out_num"] = df["company_avg_days_out"].apply(_to_float)
        df["cost_per_day_num"] = df["cost_per_day"].apply(_to_float)
        df["date_of_injury_dt"] = pd.to_datetime(df["date_of_injury"], errors="coerce")
        df["month"] = df["date_of_injury_dt"].dt.to_period("M").astype(str)
        df["quarter"] = df["date_of_injury_dt"].dt.to_period("Q").astype(str)
        df["year"] = df["date_of_injury_dt"].dt.year.astype("Int64").astype(str)
        df["terminal_display"] = df["terminal"].apply(lambda x: _safe_str(x) if _safe_str(x) else "Unassigned")
    else:
        df = pd.DataFrame(columns=["claim_number", "lag_days_num", "actual_rtw_days_num", "cost_savings_num", "month", "quarter", "year", "terminal_display"])

    total_claims = int(df["claim_number"].astype(str).str.strip().ne("").sum()) if "claim_number" in df.columns else 0
    claims_with_savings = int(df["cost_savings_num"].notna().sum()) if not df.empty else 0
    total_verified_savings = df["cost_savings_num"].dropna().sum() if not df.empty else 0
    avg_lag = df["lag_days_num"].dropna().mean() if not df.empty else None
    avg_rtw = df["actual_rtw_days_num"].dropna().mean() if not df.empty else None
    total_days_saved = ((df["company_avg_days_out_num"] - df["actual_rtw_days_num"]).clip(lower=0).dropna().sum() if not df.empty else 0)

    total_18ww_fee = total_verified_savings * fee_percent if total_verified_savings is not None else 0
    fleet_net_savings = total_verified_savings - total_18ww_fee if total_verified_savings is not None else 0

    fte_count = _derive_fte_count(fin["fte_count"], fin["man_hours"])
    total_wc_cost = fin["total_wc_cost"]
    true_cost_per_fte = (total_wc_cost / fte_count) if (total_wc_cost not in [None] and fte_count not in [None, 0]) else None
    adjusted_wc_cost = max((total_wc_cost or 0) - (total_verified_savings or 0), 0) if total_wc_cost is not None else None
    adjusted_cost_per_fte = (adjusted_wc_cost / fte_count) if (adjusted_wc_cost is not None and fte_count not in [None, 0]) else None

    profit_margin_percent = fin["profit_margin_percent"]
    avg_sale_value = fin["avg_sale_value"]
    program_cost = fin["program_cost"]
    margin_decimal = None
    if profit_margin_percent not in [None, 0]:
        margin_decimal = profit_margin_percent / 100.0 if profit_margin_percent > 1 else profit_margin_percent

    sales_pressure_removed = (total_verified_savings / margin_decimal) if (total_verified_savings is not None and margin_decimal) else None
    headline_total_improvement = total_verified_savings + (sales_pressure_removed or 0)
    revenue_needed_to_cover_program = (program_cost / margin_decimal) if (program_cost not in [None] and margin_decimal) else None
    sales_needed_to_replace_saved_loss = (sales_pressure_removed / avg_sale_value) if (sales_pressure_removed is not None and avg_sale_value not in [None, 0]) else None

    st.markdown(
        f"""
<div style="padding:20px;border-radius:14px;text-align:center;background:#065f46;color:white;">
    <div style="font-size:16px;opacity:0.85;">Headline Total Improvement</div>
    <div style="font-size:42px;font-weight:800;margin-top:6px;">{_fmt_money(headline_total_improvement)}</div>
    <div style="font-size:14px;margin-top:8px;opacity:0.85;">
        {_fmt_money(total_verified_savings)} (Savings) + {_fmt_money(sales_pressure_removed)} (Sales Pressure Removed)
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Total Verified Savings", _fmt_money(total_verified_savings))
    top2.metric("Fleet Net Savings", _fmt_money(fleet_net_savings))
    top3.metric("18WW Revenue", _fmt_money(total_18ww_fee))
    top4.metric("Fleet Keeps", f"{(1-fee_percent)*100:.0f}%")

    mid1, mid2, mid3, mid4 = st.columns(4)
    mid1.metric("Claims With Savings", claims_with_savings)
    mid2.metric("Avg Lag Time", _fmt_num(avg_lag, 1))
    mid3.metric("Avg Actual RTW Days", _fmt_num(avg_rtw, 1))
    mid4.metric("Total Days Saved", _fmt_num(total_days_saved, 1))

    low1, low2, low3, low4 = st.columns(4)
    low1.metric("True Cost per FTE", _fmt_money(true_cost_per_fte))
    low2.metric("Adjusted Cost per FTE", _fmt_money(adjusted_cost_per_fte))
    low3.metric("Sales Pressure Removed", _fmt_money(sales_pressure_removed))
    low4.metric("Revenue Needed to Cover Program", _fmt_money(revenue_needed_to_cover_program))

    final1, final2 = st.columns(2)
    final1.metric("Sales Needed to Replace Saved Loss", _fmt_num(sales_needed_to_replace_saved_loss, 1))
    final2.metric("Total Claims", total_claims)

    def build_period(period_col, label):
        work = df[df[period_col].astype(str) != "NaT"].copy()
        if work.empty:
            return pd.DataFrame(columns=[label, "Claims", "Total Savings", "18WW Fee", "Fleet Net", "Sales Pressure Removed", "Avg Lag", "Avg RTW Days"])
        grouped = (
            work.groupby(period_col, dropna=False)
            .agg(
                Claims=("claim_number", "count"),
                total_savings=("cost_savings_num", "sum"),
                avg_lag=("lag_days_num", "mean"),
                avg_rtw=("actual_rtw_days_num", "mean"),
            )
            .reset_index()
            .rename(columns={period_col: label})
            .sort_values(label)
        )
        grouped["18WW Fee"] = grouped["total_savings"] * fee_percent
        grouped["Fleet Net"] = grouped["total_savings"] - grouped["18WW Fee"]
        grouped["Sales Pressure Removed"] = grouped["total_savings"].apply(lambda x: x / margin_decimal if (margin_decimal and x is not None) else None)
        grouped = grouped.rename(columns={"total_savings": "Total Savings", "avg_lag": "Avg Lag", "avg_rtw": "Avg RTW Days"})
        return grouped

    monthly = build_period("month", "Month")
    quarterly = build_period("quarter", "Quarter")
    yearly = build_period("year", "Year")

    st.subheader("Time-Based Business Impact Rollups")
    tab1, tab2, tab3 = st.tabs(["Monthly", "Quarterly", "Yearly"])
    with tab1:
        st.dataframe(_display_rollup(monthly), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(_display_rollup(quarterly), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(_display_rollup(yearly), use_container_width=True, hide_index=True)

    if not df.empty:
        terminal_rollup = (
            df.groupby("terminal_display", dropna=False)
            .agg(
                Claims=("claim_number", "count"),
                total_savings=("cost_savings_num", "sum"),
                avg_lag=("lag_days_num", "mean"),
                avg_rtw=("actual_rtw_days_num", "mean"),
            )
            .reset_index()
            .rename(columns={"terminal_display": "Terminal"})
            .sort_values("total_savings", ascending=False)
        )
        terminal_rollup["18WW Fee"] = terminal_rollup["total_savings"] * fee_percent
        terminal_rollup["Fleet Net"] = terminal_rollup["total_savings"] - terminal_rollup["18WW Fee"]
        terminal_rollup = terminal_rollup.rename(columns={"total_savings": "Total Savings", "avg_lag": "Avg Lag", "avg_rtw": "Avg RTW Days"})
    else:
        terminal_rollup = pd.DataFrame(columns=["Terminal", "Claims", "Total Savings", "Avg Lag", "Avg RTW Days", "18WW Fee", "Fleet Net"])

    st.subheader("Terminal Comparison")
    st.dataframe(_display_rollup(terminal_rollup), use_container_width=True, hide_index=True)

    summary_rows = [
        ["Headline Total Improvement", _fmt_money(headline_total_improvement)],
        ["Total Verified Savings", _fmt_money(total_verified_savings)],
        ["Fleet Net Savings", _fmt_money(fleet_net_savings)],
        ["18WW Revenue", _fmt_money(total_18ww_fee)],
        ["Claims With Savings", claims_with_savings],
        ["Avg Lag Time", _fmt_num(avg_lag, 1)],
        ["Avg Actual RTW Days", _fmt_num(avg_rtw, 1)],
        ["Total Days Saved", _fmt_num(total_days_saved, 1)],
        ["True Cost per FTE", _fmt_money(true_cost_per_fte)],
        ["Adjusted Cost per FTE", _fmt_money(adjusted_cost_per_fte)],
        ["Sales Pressure Removed", _fmt_money(sales_pressure_removed)],
        ["Revenue Needed to Cover Program", _fmt_money(revenue_needed_to_cover_program)],
        ["Sales Needed to Replace Saved Loss", _fmt_num(sales_needed_to_replace_saved_loss, 1)],
        ["Input Source", fin["source"] or "-"],
    ]
    headline_df = pd.DataFrame(summary_rows, columns=["Metric", "Value"])

    st.subheader("Export PDFs")
    e1, e2, e3 = st.columns(3)
    with e1:
        if st.button("Build Monthly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive Business Impact - Monthly", company_name, headline_df, _display_rollup(monthly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Monthly PDF", f, file_name="18WW_Executive_Business_Impact_Monthly.pdf", mime="application/pdf", use_container_width=True)
    with e2:
        if st.button("Build Quarterly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive Business Impact - Quarterly", company_name, headline_df, _display_rollup(quarterly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Quarterly PDF", f, file_name="18WW_Executive_Business_Impact_Quarterly.pdf", mime="application/pdf", use_container_width=True)
    with e3:
        if st.button("Build Yearly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive Business Impact - Yearly", company_name, headline_df, _display_rollup(yearly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Yearly PDF", f, file_name="18WW_Executive_Business_Impact_Yearly.pdf", mime="application/pdf", use_container_width=True)

    st.subheader("Executive Summary")
    st.dataframe(headline_df, use_container_width=True, hide_index=True)

    st.success("Executive Business Impact updated with monthly, quarterly, yearly tabs and PDF exports.")
