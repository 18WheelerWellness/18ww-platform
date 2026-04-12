
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import tempfile
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from io_layer.google_company_store import load_company_rows_from_shared_tab


def _to_float(val):
    try:
        if val is None or str(val).strip() == "":
            return None
        return float(str(val).replace("$", "").replace(",", "").replace("%", ""))
    except Exception:
        return None


def _fmt_num(val, digits=1):
    num = _to_float(val)
    if num is None or pd.isna(num):
        return "-"
    if float(num).is_integer():
        return f"{int(num)}"
    return f"{num:.{digits}f}"


def _fmt_pct(val):
    num = _to_float(val)
    if num is None or pd.isna(num):
        return "-"
    return f"{num:.1f}%"


def _style_table(df):
    out = df.copy()
    for col in out.columns:
        if "RTW" in col or "Lag" in col:
            out[col] = out[col].apply(lambda x: _fmt_num(x, 1))
        if "%" in col:
            out[col] = out[col].apply(_fmt_pct)
    return out



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
    doc = SimpleDocTemplate(tmp.name, pagesize=letter)
    elements = _pdf_header_elements("Executive RTW Dashboard", company_name, "Executive return-to-work report")

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
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(table)
    
    elements.append(Paragraph(f"Company: {company_name or 'N/A'}", styles["Normal"]))

    add_table("Summary", summary_df)
    add_table("Detail Rollup", detail_df)

    doc.build(elements, onFirstPage=lambda c,d: _draw_pdf_footer(c,d,"Executive RTW Dashboard"), onLaterPages=lambda c,d: _draw_pdf_footer(c,d,"Executive RTW Dashboard"))
    return tmp.name


def render_executive_rtw_dashboard():
    st.title("Executive RTW Dashboard")
    st.caption("Executive RTW view with cleaner monthly, quarterly, and yearly reporting plus downloadable PDFs.")

    company_name = st.session_state.get("company_name", "")
    df = load_company_rows_from_shared_tab(company_name, "claims")

    if df.empty:
        st.warning("No claims data found.")
        return

    df = df.copy()
    df["rtw_days"] = df["actual_rtw_days"].apply(_to_float)
    df["lag_days"] = df["lag_days"].apply(_to_float)
    df["date"] = pd.to_datetime(df.get("date_of_injury"), errors="coerce")
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["quarter"] = df["date"].dt.to_period("Q").astype(str)
    df["year"] = df["date"].dt.year.astype("Int64").astype(str)
    if "terminal" not in df.columns:
        df["terminal"] = ""
    df["terminal"] = df["terminal"].fillna("").astype(str)
    if "claim_number" not in df.columns:
        df["claim_number"] = ""

    avg_rtw = df["rtw_days"].dropna().mean()
    avg_lag = df["lag_days"].dropna().mean()
    total_claims = int(len(df))
    valid_rtw = df["rtw_days"].dropna()
    rtw_3_pct = (valid_rtw.le(3).mean() * 100) if not valid_rtw.empty else None
    rtw_7_pct = (valid_rtw.le(7).mean() * 100) if not valid_rtw.empty else None
    employees_out = int(df["rtw_days"].isna().sum())

    st.markdown(
        f"""
<div style="padding:20px;border-radius:14px;text-align:center;background:#065f46;color:white;">
    <div style="font-size:16px;opacity:0.85;">Headline RTW Performance</div>
    <div style="font-size:42px;font-weight:800;margin-top:6px;">{_fmt_pct(rtw_7_pct)}</div>
    <div style="font-size:14px;margin-top:8px;opacity:0.85;">
        RTW ≤ 7 Days • Avg RTW {_fmt_num(avg_rtw, 1)} • Avg Lag {_fmt_num(avg_lag, 1)}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("RTW ≤ 3 Days", _fmt_pct(rtw_3_pct))
    col2.metric("RTW ≤ 7 Days", _fmt_pct(rtw_7_pct))
    col3.metric("Avg RTW Days", _fmt_num(avg_rtw, 1))
    col4.metric("Avg Lag Time", _fmt_num(avg_lag, 1))

    col5, col6 = st.columns(2)
    col5.metric("Employees Out of Work", employees_out)
    col6.metric("Total Claims", total_claims)

    def build_period(period_col, label):
        work = df[df[period_col].astype(str) != "NaT"].copy()
        if work.empty:
            return pd.DataFrame(columns=[label, "Claims", "RTW ≤ 3 Days %", "RTW ≤ 7 Days %", "Avg RTW Days", "Avg Lag Time", "Employees Out"])
        grouped = (
            work.groupby(period_col)
            .agg(
                Claims=("claim_number", "count"),
                avg_rtw_days=("rtw_days", "mean"),
                avg_lag_time=("lag_days", "mean"),
                employees_out=("rtw_days", lambda s: int(s.isna().sum())),
                rtw_3_pct=("rtw_days", lambda s: s.dropna().le(3).mean() * 100 if s.dropna().shape[0] else None),
                rtw_7_pct=("rtw_days", lambda s: s.dropna().le(7).mean() * 100 if s.dropna().shape[0] else None),
            )
            .reset_index()
            .rename(columns={
                period_col: label,
                "avg_rtw_days": "Avg RTW Days",
                "avg_lag_time": "Avg Lag Time",
                "employees_out": "Employees Out",
                "rtw_3_pct": "RTW ≤ 3 Days %",
                "rtw_7_pct": "RTW ≤ 7 Days %",
            })
            .sort_values(label)
        )
        return grouped

    monthly = build_period("month", "Month")
    quarterly = build_period("quarter", "Quarter")
    yearly = build_period("year", "Year")

    st.subheader("Time-Based RTW Rollups")
    tab1, tab2, tab3 = st.tabs(["Monthly", "Quarterly", "Yearly"])
    with tab1:
        st.dataframe(_style_table(monthly), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(_style_table(quarterly), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(_style_table(yearly), use_container_width=True, hide_index=True)

    if not monthly.empty:
        fig, ax = plt.subplots()
        ax.plot(monthly["Month"], monthly["Avg RTW Days"], label="Avg RTW")
        ax.plot(monthly["Month"], monthly["Avg Lag Time"], label="Avg Lag")
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        ax.set_title("RTW and Lag Trend by Month")
        st.pyplot(fig)

    if df["terminal"].str.strip().ne("").any():
        terminal = (
            df.groupby("terminal")
            .agg(
                avg_rtw_days=("rtw_days", "mean"),
                avg_lag_time=("lag_days", "mean"),
                claims=("claim_number", "count"),
            )
            .reset_index()
            .rename(columns={
                "terminal": "Terminal",
                "avg_rtw_days": "Avg RTW Days",
                "avg_lag_time": "Avg Lag Time",
                "claims": "Claims",
            })
            .sort_values("Claims", ascending=False)
        )
        st.subheader("Terminal Comparison")
        st.dataframe(_style_table(terminal), use_container_width=True, hide_index=True)

    summary_df = pd.DataFrame([
        ["RTW ≤ 3 Days", _fmt_pct(rtw_3_pct)],
        ["RTW ≤ 7 Days", _fmt_pct(rtw_7_pct)],
        ["Avg RTW Days", _fmt_num(avg_rtw, 1)],
        ["Avg Lag Time", _fmt_num(avg_lag, 1)],
        ["Employees Out of Work", employees_out],
        ["Total Claims", total_claims],
    ], columns=["Metric", "Value"])

    st.subheader("Export PDFs")
    e1, e2, e3 = st.columns(3)
    with e1:
        if st.button("Build Monthly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive RTW Dashboard - Monthly", company_name, summary_df, _style_table(monthly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Monthly PDF", data=f, file_name="18WW_Executive_RTW_Dashboard_Monthly.pdf", mime="application/pdf", use_container_width=True)
    with e2:
        if st.button("Build Quarterly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive RTW Dashboard - Quarterly", company_name, summary_df, _style_table(quarterly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Quarterly PDF", data=f, file_name="18WW_Executive_RTW_Dashboard_Quarterly.pdf", mime="application/pdf", use_container_width=True)
    with e3:
        if st.button("Build Yearly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive RTW Dashboard - Yearly", company_name, summary_df, _style_table(yearly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Yearly PDF", data=f, file_name="18WW_Executive_RTW_Dashboard_Yearly.pdf", mime="application/pdf", use_container_width=True)

    st.subheader("Executive Summary")
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.success("Executive RTW Dashboard built successfully.")
