
import streamlit as st
import pandas as pd
import numpy as np
import tempfile
import os

from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from io_layer.google_company_store import load_company_rows_from_shared_tab

PDF_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "18ww_logo.png")


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


def _fmt_num(val, digits=1):
    if val is None or pd.isna(val):
        return "-"
    if isinstance(val, float) and not float(val).is_integer():
        return f"{val:.{digits}f}"
    return f"{int(val)}"


def _load_fms(company_name: str) -> pd.DataFrame:
    try:
        df = load_company_rows_from_shared_tab(company_name, "FMS")
    except Exception:
        return pd.DataFrame()

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
        if col not in ["front_score", "side_score", "back_score", "total_score"]:
            df[col] = df[col].apply(_safe_text)

    for col in ["front_score", "side_score", "back_score", "total_score"]:
        df[col] = df[col].apply(_to_float)

    df["assessment_dt"] = pd.to_datetime(df["assessment_date"], errors="coerce")
    df["month"] = df["assessment_dt"].dt.to_period("M").astype(str)
    df["quarter"] = df["assessment_dt"].dt.to_period("Q").astype(str)
    df["year"] = df["assessment_dt"].dt.year.astype("Int64").astype(str)
    return df


def _pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="IssueTitle",
        parent=styles["Heading3"],
        fontSize=11,
        leading=13,
        spaceAfter=4,
        textColor=colors.HexColor("#0F1B38"),
    ))
    styles.add(ParagraphStyle(
        name="IssueBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=12,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        name="TakeawayBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=13,
        spaceAfter=4,
    ))
    return styles


def _pdf_header_elements(title, company_name, subtitle="Executive report"):
    styles = _pdf_styles()
    elements = []

    logo_cell = ""
    if os.path.exists(PDF_LOGO_PATH):
        try:
            logo_cell = RLImage(PDF_LOGO_PATH, width=1.0 * inch, height=1.0 * inch)
        except Exception:
            logo_cell = ""

    title_html = (
        f"<b>{title}</b><br/>"
        f"Company: {_safe_text(company_name) or 'N/A'}<br/>"
        f"Generated: {datetime.now().strftime('%Y-%m-%d')}<br/>"
        f"<i>{subtitle}</i>"
    )

    header_table = Table([[logo_cell, Paragraph(title_html, styles["Normal"])]], colWidths=[1.0 * inch, 8.8 * inch])
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


def _draw_pdf_footer(canvas, doc, report_name="Executive FMS Dashboard"):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#52606F"))
    canvas.drawString(doc.leftMargin, 20, f"18WW | {report_name}")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 20, f"Page {doc.page}")
    canvas.restoreState()


def _issue_impact_text(issue: str) -> str:
    issue_l = _safe_text(issue).lower()
    mappings = [
        (["neck", "cervical", "rotation"], "Can limit mirror checks, blind-spot scanning, and backing visibility."),
        (["shoulder", "reach", "thoracic"], "Can reduce steering-wheel comfort, overhead reach, and load securement tolerance."),
        (["low back", "lumbar", "back"], "Can reduce sitting tolerance, vibration tolerance, and safe cab entry and exit."),
        (["hip", "knee", "ankle"], "Can affect climbing into the cab, stair use, braking mechanics, and trailer access."),
        (["wrist", "elbow", "grip"], "Can reduce grip endurance for steering, latches, straps, and coupling tasks."),
        (["posture", "forward head", "rounded"], "Can increase fatigue over long drives and reduce efficient driving posture."),
    ]
    for keys, txt in mappings:
        if any(k in issue_l for k in keys):
            return txt
    return "May reduce movement efficiency, driving tolerance, and safe execution of daily CDL tasks."


def _priority_action_text(issue: str) -> str:
    issue_l = _safe_text(issue).lower()
    mappings = [
        (["neck", "cervical", "rotation"], "Prioritize cervical mobility, thoracic rotation work, and mirror-check pattern retraining."),
        (["shoulder", "reach", "thoracic"], "Prioritize shoulder mobility, thoracic extension and rotation, and reach-pattern correction."),
        (["low back", "lumbar", "back"], "Prioritize trunk control, hip mobility, and sitting-tolerance strategies."),
        (["hip", "knee", "ankle"], "Prioritize lower-extremity mobility, step mechanics, and cab-entry movement quality."),
        (["wrist", "elbow", "grip"], "Prioritize grip endurance, forearm mobility, and task-specific hand strength."),
        (["posture", "forward head", "rounded"], "Prioritize posture reset work, scapular control, and cab-positioning changes."),
    ]
    for keys, txt in mappings:
        if any(k in issue_l for k in keys):
            return txt
    return "Prioritize corrective exercise, targeted mobility, and repeated movement-quality reassessment."


def _build_biggest_issues_section(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Issue", "Frequency", "Likely Driver Impact", "Corrective Focus"])

    issue_source = None
    for col in ["findings_summary", "corrective_priorities", "overall_risk", "session_tag"]:
        if col in df.columns:
            issue_source = col
            break
    if issue_source is None:
        return pd.DataFrame(columns=["Issue", "Frequency", "Likely Driver Impact", "Corrective Focus"])

    issues = (
        df[issue_source]
        .fillna("")
        .astype(str)
        .str.split(r"[;,|]")
        .explode()
        .astype(str)
        .str.strip()
    )
    issues = issues[issues != ""]
    if issues.empty:
        return pd.DataFrame(columns=["Issue", "Frequency", "Likely Driver Impact", "Corrective Focus"])

    top = issues.value_counts().head(5).reset_index()
    top.columns = ["Issue", "Frequency"]
    top["Likely Driver Impact"] = top["Issue"].apply(_issue_impact_text)
    top["Corrective Focus"] = top["Issue"].apply(_priority_action_text)
    return top


def _build_executive_takeaway(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Takeaway", "Value"])

    total_screens = len(df)
    avg_total = df["total_score"].dropna().mean() if "total_score" in df.columns and not df["total_score"].dropna().empty else None
    latest_date = df["assessment_dt"].max().strftime("%Y-%m-%d") if "assessment_dt" in df.columns and df["assessment_dt"].notna().any() else "-"
    high_risk = int(df["overall_risk"].astype(str).str.lower().isin(["high"]).sum()) if "overall_risk" in df.columns else 0

    issues_df = _build_biggest_issues_section(df)
    top_issue = issues_df.iloc[0]["Issue"] if not issues_df.empty else "-"

    rows = [
        ["Screens Included", total_screens],
        ["Average Total Score", _fmt_num(avg_total, 1)],
        ["High-Risk Screens", high_risk],
        ["Top Repeated Issue", top_issue],
        ["Latest Assessment", latest_date],
    ]
    return pd.DataFrame(rows, columns=["Takeaway", "Value"])


def _build_pdf(title, subtitle, report_name, company_name, headline_df, detail_df, source_df=None):
    styles = _pdf_styles()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(
        tmp.name,
        pagesize=landscape(letter),
        leftMargin=24,
        rightMargin=24,
        topMargin=28,
        bottomMargin=28,
    )
    elements = _pdf_header_elements(title, company_name, subtitle)

    def add_table(title_text, df):
        elements.append(Paragraph(title_text, styles["Heading2"]))
        if df is None or df.empty:
            elements.append(Paragraph("No data available.", styles["Normal"]))
            elements.append(Spacer(1, 10))
            return

        table_data = [list(df.columns)] + df.astype(str).values.tolist()
        ncols = max(len(df.columns), 1)
        usable_width = 10.0 * inch
        col_widths = [usable_width / ncols] * ncols

        if title_text == "Headline Metrics":
            col_widths = [3.6 * inch, 1.6 * inch]

        table = Table(table_data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("LEADING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 12))

    def add_takeaway_box(df_takeaway):
        elements.append(Paragraph("Executive Takeaway", styles["Heading2"]))
        for _, row in df_takeaway.iterrows():
            txt = f"<b>{row['Takeaway']}:</b> {row['Value']}"
            elements.append(Paragraph(txt, styles["TakeawayBody"]))
        elements.append(Spacer(1, 8))

    def add_issue_cards(df_issues):
        elements.append(Paragraph("Biggest Issues & Driver Impact", styles["Heading2"]))
        if df_issues.empty:
            elements.append(Paragraph("No issues available.", styles["BodyText"]))
            elements.append(Spacer(1, 10))
            return

        for _, row in df_issues.iterrows():
            issue = _safe_text(row.get("Issue"))
            freq = _safe_text(row.get("Frequency"))
            impact = _safe_text(row.get("Likely Driver Impact"))
            focus = _safe_text(row.get("Corrective Focus"))

            card = Table([[
                Paragraph(f"<b>{issue}</b>  |  Seen {freq} time(s)", styles["IssueTitle"]),
                ""
            ], [
                Paragraph(f"<b>Likely Driver Impact:</b> {impact}", styles["IssueBody"]),
                Paragraph(f"<b>Corrective Focus:</b> {focus}", styles["IssueBody"]),
            ]], colWidths=[4.9 * inch, 4.9 * inch])

            card.setStyle(TableStyle([
                ("SPAN", (0, 0), (1, 0)),
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#EEF1F8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(card)
            elements.append(Spacer(1, 8))

    add_table("Headline Metrics", headline_df)

    if source_df is not None:
        takeaway_df = _build_executive_takeaway(source_df)
        issues_df = _build_biggest_issues_section(source_df)
        add_takeaway_box(takeaway_df)
        add_issue_cards(issues_df)

    add_table("Detail Rollup", detail_df)

    doc.build(
        elements,
        onFirstPage=lambda c, d: _draw_pdf_footer(c, d, report_name),
        onLaterPages=lambda c, d: _draw_pdf_footer(c, d, report_name),
    )
    return tmp.name


def _style_rollup(df_in):
    out = df_in.copy()
    if out.empty:
        return out
    for col in ["Avg Front Score", "Avg Side Score", "Avg Back Score", "Avg Total Score"]:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: _fmt_num(x, 1))
    return out


def _build_period_rollup(df: pd.DataFrame, period_col: str, label: str) -> pd.DataFrame:
    work = df[df[period_col].astype(str) != "NaT"].copy()
    work = work[work[period_col].astype(str) != "<NA>"].copy()
    if work.empty:
        return pd.DataFrame(columns=[label, "Screens", "Drivers", "Avg Front Score", "Avg Side Score", "Avg Back Score", "Avg Total Score"])
    grouped = (
        work.groupby(period_col, dropna=False)
        .agg(
            Screens=("driver_name", "count"),
            Drivers=("driver_name", lambda s: s.astype(str).str.strip().replace("", np.nan).dropna().nunique()),
            front_score=("front_score", "mean"),
            side_score=("side_score", "mean"),
            back_score=("back_score", "mean"),
            total_score=("total_score", "mean"),
        )
        .reset_index()
        .rename(columns={
            period_col: label,
            "front_score": "Avg Front Score",
            "side_score": "Avg Side Score",
            "back_score": "Avg Back Score",
            "total_score": "Avg Total Score",
        })
        .sort_values(label)
    )
    return grouped


def render_executive_fms_dashboard():
    st.title("Executive FMS Dashboard")
    st.caption("Executive FMS view with monthly, quarterly, and yearly rollups plus downloadable PDF exports.")

    company_name = st.session_state.get("company_name", "")
    df = _load_fms(company_name)

    if df.empty:
        st.info("No FMS data found yet.")
        return

    total_screens = int(len(df))
    drivers = int(df["driver_name"].astype(str).str.strip().replace("", np.nan).dropna().nunique())
    avg_front = df["front_score"].dropna().mean() if not df["front_score"].dropna().empty else None
    avg_side = df["side_score"].dropna().mean() if not df["side_score"].dropna().empty else None
    avg_back = df["back_score"].dropna().mean() if not df["back_score"].dropna().empty else None
    avg_total = df["total_score"].dropna().mean() if not df["total_score"].dropna().empty else None
    latest_date = df["assessment_dt"].max().strftime("%Y-%m-%d") if df["assessment_dt"].notna().any() else "-"

    st.markdown(
        f"""
<div style="padding:20px;border-radius:14px;text-align:center;background:#065f46;color:white;">
    <div style="font-size:16px;opacity:0.85;">Headline FMS Performance</div>
    <div style="font-size:42px;font-weight:800;margin-top:6px;">{_fmt_num(avg_total, 1)}</div>
    <div style="font-size:14px;margin-top:8px;opacity:0.85;">
        Avg Total Score • Front {_fmt_num(avg_front,1)} • Side {_fmt_num(avg_side,1)} • Back {_fmt_num(avg_back,1)}
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("FMS Screens", total_screens)
    m2.metric("Drivers Screened", drivers)
    m3.metric("Avg Total Score", _fmt_num(avg_total, 1))
    m4.metric("Latest Assessment", latest_date)

    m5, m6, m7 = st.columns(3)
    m5.metric("Avg Front Score", _fmt_num(avg_front, 1))
    m6.metric("Avg Side Score", _fmt_num(avg_side, 1))
    m7.metric("Avg Back Score", _fmt_num(avg_back, 1))

    st.subheader("Time-Based FMS Rollups")
    monthly = _build_period_rollup(df, "month", "Month")
    quarterly = _build_period_rollup(df, "quarter", "Quarter")
    yearly = _build_period_rollup(df, "year", "Year")

    tab1, tab2, tab3 = st.tabs(["Monthly", "Quarterly", "Yearly"])
    with tab1:
        st.dataframe(_style_rollup(monthly), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(_style_rollup(quarterly), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(_style_rollup(yearly), use_container_width=True, hide_index=True)

    st.subheader("Recent FMS Records")
    recent = df.sort_values("assessment_dt", ascending=False)[[
        "driver_name", "driver_id", "assessment_date", "front_score", "side_score", "back_score",
        "total_score", "overall_risk", "findings_summary",
    ]].head(25).copy()
    recent = _style_rollup(recent)
    st.dataframe(recent, use_container_width=True, hide_index=True)

    summary_df = pd.DataFrame([
        ["FMS Screens", total_screens],
        ["Drivers Screened", drivers],
        ["Avg Front Score", _fmt_num(avg_front, 1)],
        ["Avg Side Score", _fmt_num(avg_side, 1)],
        ["Avg Back Score", _fmt_num(avg_back, 1)],
        ["Avg Total Score", _fmt_num(avg_total, 1)],
        ["Latest Assessment", latest_date],
    ], columns=["Metric", "Value"])

    st.subheader("Export PDFs")
    e1, e2, e3 = st.columns(3)
    with e1:
        if st.button("Build Monthly PDF", use_container_width=True):
            pdf_path = _build_pdf(
                "18WW Executive FMS Dashboard - Monthly",
                "Executive monthly FMS report",
                "Executive FMS Monthly",
                company_name,
                summary_df,
                _style_rollup(monthly),
                source_df=df,
            )
            if pdf_path:
                with open(pdf_path, "rb") as f:
                    st.download_button("Download Monthly PDF", f, file_name="18WW_Executive_FMS_Monthly.pdf", mime="application/pdf", use_container_width=True)
    with e2:
        if st.button("Build Quarterly PDF", use_container_width=True):
            pdf_path = _build_pdf(
                "18WW Executive FMS Dashboard - Quarterly",
                "Executive quarterly FMS report",
                "Executive FMS Quarterly",
                company_name,
                summary_df,
                _style_rollup(quarterly),
                source_df=df,
            )
            if pdf_path:
                with open(pdf_path, "rb") as f:
                    st.download_button("Download Quarterly PDF", f, file_name="18WW_Executive_FMS_Quarterly.pdf", mime="application/pdf", use_container_width=True)
    with e3:
        if st.button("Build Yearly PDF", use_container_width=True):
            pdf_path = _build_pdf(
                "18WW Executive FMS Dashboard - Yearly",
                "Executive yearly FMS report",
                "Executive FMS Yearly",
                company_name,
                summary_df,
                _style_rollup(yearly),
                source_df=df,
            )
            if pdf_path:
                with open(pdf_path, "rb") as f:
                    st.download_button("Download Yearly PDF", f, file_name="18WW_Executive_FMS_Yearly.pdf", mime="application/pdf", use_container_width=True)

    st.success("Executive FMS Dashboard now includes cleaner monthly, quarterly, and yearly PDF exports.")
