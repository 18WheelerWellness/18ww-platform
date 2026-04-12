
import streamlit as st
import pandas as pd
import tempfile
from datetime import datetime

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from io_layer.google_company_store import load_company_rows_from_shared_tab


def _safe_text(val):
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def _to_float(val):
    try:
        text = _safe_text(val).replace("$", "").replace(",", "").replace("%", "")
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


def _fmt_pct(val):
    if val is None or pd.isna(val):
        return "-"
    return f"{val:.1f}%"



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

def _build_pdf(title, company_name, summary_df, detail_df):
    styles = getSampleStyleSheet()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=landscape(letter), leftMargin=24, rightMargin=24, topMargin=28, bottomMargin=28)
    elements = _pdf_header_elements("Operations Reports", company_name, "Operations reporting center")

    def add_table(title_text, df):
        elements.append(Paragraph(title_text, styles["Heading2"]))
        if df is None or df.empty:
            elements.append(Paragraph("No data available.", styles["Normal"]))
            elements.append(Spacer(1, 10))
            return
        table_data = [df.columns.tolist()] + df.astype(str).values.tolist()
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("LEADING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
        ]))
        elements.append(table)
    
    add_table("Summary", summary_df)
    add_table("Detail", detail_df)

    doc.build(elements, onFirstPage=lambda c,d: _draw_pdf_footer(c,d,"Operations Reports"), onLaterPages=lambda c,d: _draw_pdf_footer(c,d,"Operations Reports"))
    return tmp.name


def _load_claims(company_name):
    df = load_company_rows_from_shared_tab(company_name, "claims")
    if df.empty:
        return df

    needed = [
        "claim_number", "driver_name", "date_of_injury", "claim_stage", "claim_status",
        "lag_days", "actual_rtw_days", "cost_savings_by_claim", "company_avg_days_out",
        "cost_per_day", "terminal", "injury_area",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""

    for col in needed:
        df[col] = df[col].apply(_safe_text)

    df["lag_days_num"] = df["lag_days"].apply(_to_float)
    df["actual_rtw_days_num"] = df["actual_rtw_days"].apply(_to_float)
    df["cost_savings_num"] = df["cost_savings_by_claim"].apply(_to_float)
    df["date_of_injury_dt"] = pd.to_datetime(df["date_of_injury"], errors="coerce")
    return df


def _load_fms(company_name):
    df = load_company_rows_from_shared_tab(company_name, "FMS")
    if df.empty:
        return df

    needed = [
        "driver_name", "driver_id", "assessment_date", "session_tag", "assessor",
        "front_score", "side_score", "back_score", "total_score", "overall_risk",
        "findings_summary", "corrective_priorities",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].apply(_safe_text)

    for col in ["front_score", "side_score", "back_score", "total_score"]:
        df[f"{col}_num"] = df[col].apply(_to_float)

    return df


def _load_rom_mmi(company_name):
    df = load_company_rows_from_shared_tab(company_name, "rom_mmi")
    if df.empty:
        return df

    needed = [
        "state", "driver_name", "driver_id", "claim_number", "body_part", "movement",
        "baseline_rom_deg", "post_injury_rom_deg", "deficit_vs_baseline_pct",
        "protected_value_conservative", "protected_value_expected", "protected_value_aggressive",
        "status", "assessment_date",
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = ""
        if "value" not in col and "pct" not in col and "deg" not in col:
            df[col] = df[col].apply(_safe_text)

    for col in [
        "baseline_rom_deg", "post_injury_rom_deg", "deficit_vs_baseline_pct",
        "protected_value_conservative", "protected_value_expected", "protected_value_aggressive",
    ]:
        df[f"{col}_num"] = df[col].apply(_to_float)

    return df


def show_reports():
    company_name = st.session_state.get("company_name", "")
    if not company_name:
        st.error("No company assigned. Please log in again.")
        st.stop()

    st.title("Reports")
    st.caption("Launch-ready report center for Claims, RTW, FMS, and ROM/MMI.")

    claims_df = _load_claims(company_name)
    fms_df = _load_fms(company_name)
    rom_df = _load_rom_mmi(company_name)

    if claims_df.empty and fms_df.empty and rom_df.empty:
        st.warning("No live report data found yet.")
        st.caption("Add claims, FMS, or ROM/MMI records first.")
        return

    total_claims = int(len(claims_df)) if not claims_df.empty else 0
    total_savings = claims_df["cost_savings_num"].dropna().sum() if not claims_df.empty else 0
    avg_lag = claims_df["lag_days_num"].dropna().mean() if not claims_df.empty else None
    avg_rtw = claims_df["actual_rtw_days_num"].dropna().mean() if not claims_df.empty else None

    total_fms = int(len(fms_df)) if not fms_df.empty else 0
    avg_fms_score = fms_df["total_score_num"].dropna().mean() if not fms_df.empty else None

    total_rom_rows = int(len(rom_df)) if not rom_df.empty else 0
    protected_expected = rom_df["protected_value_expected_num"].dropna().sum() if not rom_df.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Claims", total_claims)
    m2.metric("Claim Savings", _fmt_money(total_savings))
    m3.metric("FMS Screens", total_fms)
    m4.metric("ROM/MMI Protected Value", _fmt_money(protected_expected))

    m5, m6, m7 = st.columns(3)
    m5.metric("Avg Lag Time", _fmt_num(avg_lag, 1))
    m6.metric("Avg RTW Days", _fmt_num(avg_rtw, 1))
    m7.metric("Avg FMS Score", _fmt_num(avg_fms_score, 1))

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Claims Report",
        "RTW Report",
        "FMS Report",
        "ROM/MMI Report",
        "Company Summary",
    ])

    with tab1:
        st.subheader("Claims Report")
        claim_display = claims_df[[
            "claim_number", "driver_name", "date_of_injury", "injury_area",
            "claim_stage", "claim_status", "lag_days", "actual_rtw_days",
            "cost_savings_by_claim", "terminal",
        ]].copy() if not claims_df.empty else pd.DataFrame()
        st.dataframe(claim_display, use_container_width=True, hide_index=True)

        summary_df = pd.DataFrame([
            ["Claims", total_claims],
            ["Claim Savings", _fmt_money(total_savings)],
            ["Avg Lag Time", _fmt_num(avg_lag, 1)],
            ["Avg RTW Days", _fmt_num(avg_rtw, 1)],
        ], columns=["Metric", "Value"])

        c1, c2 = st.columns(2)
        with c1:
            if not claim_display.empty:
                st.download_button("Download Claims CSV", claim_display.to_csv(index=False).encode("utf-8"), "claims_report.csv", "text/csv", use_container_width=True)
        with c2:
            if st.button("Build Claims PDF", use_container_width=True):
                pdf_path = _build_pdf("18WW Claims Report", company_name, summary_df, claim_display)
                with open(pdf_path, "rb") as f:
                    st.download_button("Download Claims PDF", f, "18WW_Claims_Report.pdf", "application/pdf", use_container_width=True)

    with tab2:
        st.subheader("RTW Report")
        if not claims_df.empty:
            rtw_display = claims_df[[
                "claim_number", "driver_name", "date_of_injury", "claim_stage",
                "lag_days", "actual_rtw_days", "company_avg_days_out",
                "cost_per_day", "cost_savings_by_claim", "terminal",
            ]].copy()
        else:
            rtw_display = pd.DataFrame()

        st.dataframe(rtw_display, use_container_width=True, hide_index=True)

        summary_df = pd.DataFrame([
            ["Avg RTW Days", _fmt_num(avg_rtw, 1)],
            ["Avg Lag Time", _fmt_num(avg_lag, 1)],
            ["Total RTW Savings", _fmt_money(total_savings)],
        ], columns=["Metric", "Value"])

        c1, c2 = st.columns(2)
        with c1:
            if not rtw_display.empty:
                st.download_button("Download RTW CSV", rtw_display.to_csv(index=False).encode("utf-8"), "rtw_report.csv", "text/csv", use_container_width=True)
        with c2:
            if st.button("Build RTW PDF", use_container_width=True):
                pdf_path = _build_pdf("18WW RTW Report", company_name, summary_df, rtw_display)
                with open(pdf_path, "rb") as f:
                    st.download_button("Download RTW PDF", f, "18WW_RTW_Report.pdf", "application/pdf", use_container_width=True)

    with tab3:
        st.subheader("FMS Report")
        fms_display = fms_df[[
            "driver_name", "driver_id", "assessment_date", "session_tag", "assessor",
            "front_score", "side_score", "back_score", "total_score", "overall_risk",
            "findings_summary", "corrective_priorities",
        ]].copy() if not fms_df.empty else pd.DataFrame()

        st.dataframe(fms_display, use_container_width=True, hide_index=True)

        summary_df = pd.DataFrame([
            ["FMS Screens", total_fms],
            ["Avg FMS Score", _fmt_num(avg_fms_score, 1)],
        ], columns=["Metric", "Value"])

        c1, c2 = st.columns(2)
        with c1:
            if not fms_display.empty:
                st.download_button("Download FMS CSV", fms_display.to_csv(index=False).encode("utf-8"), "fms_report.csv", "text/csv", use_container_width=True)
        with c2:
            if st.button("Build FMS PDF", use_container_width=True):
                pdf_path = _build_pdf("18WW FMS Report", company_name, summary_df, fms_display)
                with open(pdf_path, "rb") as f:
                    st.download_button("Download FMS PDF", f, "18WW_FMS_Report.pdf", "application/pdf", use_container_width=True)

    with tab4:
        st.subheader("ROM/MMI Report")
        rom_display = rom_df[[
            "state", "driver_name", "driver_id", "claim_number", "body_part", "movement",
            "baseline_rom_deg", "post_injury_rom_deg", "deficit_vs_baseline_pct",
            "protected_value_conservative", "protected_value_expected", "protected_value_aggressive",
            "status", "assessment_date",
        ]].copy() if not rom_df.empty else pd.DataFrame()

        st.dataframe(rom_display, use_container_width=True, hide_index=True)

        summary_df = pd.DataFrame([
            ["ROM/MMI Rows", total_rom_rows],
            ["Protected Value - Expected", _fmt_money(protected_expected)],
        ], columns=["Metric", "Value"])

        c1, c2 = st.columns(2)
        with c1:
            if not rom_display.empty:
                st.download_button("Download ROM/MMI CSV", rom_display.to_csv(index=False).encode("utf-8"), "rom_mmi_report.csv", "text/csv", use_container_width=True)
        with c2:
            if st.button("Build ROM/MMI PDF", use_container_width=True):
                pdf_path = _build_pdf("18WW ROM/MMI Report", company_name, summary_df, rom_display)
                with open(pdf_path, "rb") as f:
                    st.download_button("Download ROM/MMI PDF", f, "18WW_ROM_MMI_Report.pdf", "application/pdf", use_container_width=True)

    with tab5:
        st.subheader("Company Summary")
        company_summary = pd.DataFrame([
            ["Company", company_name],
            ["Claims", total_claims],
            ["Claim Savings", _fmt_money(total_savings)],
            ["Avg Lag Time", _fmt_num(avg_lag, 1)],
            ["Avg RTW Days", _fmt_num(avg_rtw, 1)],
            ["FMS Screens", total_fms],
            ["Avg FMS Score", _fmt_num(avg_fms_score, 1)],
            ["ROM/MMI Rows", total_rom_rows],
            ["ROM/MMI Protected Value", _fmt_money(protected_expected)],
        ], columns=["Metric", "Value"])
        st.dataframe(company_summary, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download Company Summary CSV", company_summary.to_csv(index=False).encode("utf-8"), "company_summary_report.csv", "text/csv", use_container_width=True)
        with c2:
            if st.button("Build Company Summary PDF", use_container_width=True):
                pdf_path = _build_pdf("18WW Company Summary Report", company_name, company_summary, pd.DataFrame())
                with open(pdf_path, "rb") as f:
                    st.download_button("Download Company Summary PDF", f, "18WW_Company_Summary_Report.pdf", "application/pdf", use_container_width=True)
