
import streamlit as st
import pandas as pd
import numpy as np
import tempfile
import os

from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from io_layer.google_company_store import load_company_rows_from_shared_tab

ROM_MMI_TAB_NAME = "rom_mmi"
PDF_LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "18ww_logo.png")

BRAND_NAVY = "#0F1B38"
BRAND_SILVER = "#EEF1F8"
BRAND_SLATE = "#52606F"


def _safe_text(val) -> str:
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def _to_float(val):
    try:
        text = _safe_text(val).replace("%", "").replace("$", "").replace(",", "")
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def _fmt_money(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"${val:,.0f}"


def _fmt_pct(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"{val:.1f}%"


def _load_rom_mmi(company_name: str) -> pd.DataFrame:
    try:
        df = load_company_rows_from_shared_tab(company_name, ROM_MMI_TAB_NAME)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    expected_cols = [
        "company_name", "state", "driver_id", "driver_name", "claim_number",
        "body_part", "movement", "side", "standard_rom_deg", "baseline_rom_deg",
        "post_injury_rom_deg", "deficit_vs_standard_deg", "deficit_vs_standard_pct",
        "deficit_vs_baseline_deg", "deficit_vs_baseline_pct",
        "impairment_estimate_without_baseline_pct", "impairment_estimate_with_baseline_pct",
        "value_without_baseline_conservative", "value_with_baseline_conservative", "protected_value_conservative",
        "value_without_baseline_expected", "value_with_baseline_expected", "protected_value_expected",
        "value_without_baseline_aggressive", "value_with_baseline_aggressive", "protected_value_aggressive",
        "status", "assessment_date", "assessor", "notes",
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    text_cols = [
        "company_name", "state", "driver_id", "driver_name", "claim_number",
        "body_part", "movement", "side", "status", "assessment_date", "assessor", "notes",
    ]
    for col in text_cols:
        df[col] = df[col].apply(_safe_text)

    numeric_cols = [
        "standard_rom_deg", "baseline_rom_deg", "post_injury_rom_deg",
        "deficit_vs_standard_deg", "deficit_vs_standard_pct",
        "deficit_vs_baseline_deg", "deficit_vs_baseline_pct",
        "impairment_estimate_without_baseline_pct", "impairment_estimate_with_baseline_pct",
        "value_without_baseline_conservative", "value_with_baseline_conservative", "protected_value_conservative",
        "value_without_baseline_expected", "value_with_baseline_expected", "protected_value_expected",
        "value_without_baseline_aggressive", "value_with_baseline_aggressive", "protected_value_aggressive",
    ]
    for col in numeric_cols:
        df[col] = df[col].apply(_to_float)

    df["assessment_dt"] = pd.to_datetime(df["assessment_date"], errors="coerce")
    df["month"] = df["assessment_dt"].dt.to_period("M").astype(str)
    df["quarter"] = df["assessment_dt"].dt.to_period("Q").astype(str)
    df["year"] = df["assessment_dt"].dt.year.astype("Int64").astype(str)
    return df


def _top_counts(series: pd.Series, top_n: int = 8, item_name: str = "Item") -> pd.DataFrame:
    cleaned = series.dropna().astype(str).str.strip()
    cleaned = cleaned[cleaned != ""]
    if cleaned.empty:
        return pd.DataFrame(columns=[item_name, "Count"])
    out = cleaned.value_counts().head(top_n).reset_index()
    out.columns = [item_name, "Count"]
    return out


def _driver_label(row) -> str:
    name = _safe_text(row.get("driver_name"))
    driver_id = _safe_text(row.get("driver_id"))
    if driver_id:
        return f"{name} ({driver_id})" if name else driver_id
    return name


def _pdf_header_elements(title, company_name, subtitle="Executive report"):
    styles = getSampleStyleSheet()
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
    header_table = Table([[logo_cell, Paragraph(title_html, styles["Normal"])]], colWidths=[1.2 * inch, 5.8 * inch])
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


def _draw_pdf_footer(canvas, doc, report_name="Executive ROM/MMI"):
    canvas.saveState()
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#52606F"))
    canvas.drawString(doc.leftMargin, 20, f"18WW | {report_name}")
    canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 20, f"Page {doc.page}")
    canvas.restoreState()


def _build_pdf(title, subtitle, report_name, company_name, headline_df, detail_df):
    styles = getSampleStyleSheet()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=landscape(letter), leftMargin=24, rightMargin=24, topMargin=28, bottomMargin=28)
    elements = _pdf_header_elements(title, company_name, subtitle)

    def add_table(title_text, df):
        elements.append(Paragraph(title_text, styles["Heading2"]))
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
        elements.append(Spacer(1, 12))

    add_table("Headline Metrics", headline_df)
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
    for col in ["Protected $ Conservative", "Protected $ Expected", "Protected $ Aggressive"]:
        if col in out.columns:
            out[col] = out[col].apply(_fmt_money)
    for col in ["Avg Deficit vs Baseline", "Avg Deficit vs Standard"]:
        if col in out.columns:
            out[col] = out[col].apply(_fmt_pct)
    return out


def _build_period_rollup(df: pd.DataFrame, period_col: str, label: str) -> pd.DataFrame:
    work = df[df[period_col].astype(str) != "NaT"].copy()
    work = work[work[period_col].astype(str) != "<NA>"].copy()
    if work.empty:
        return pd.DataFrame(columns=[label, "Rows", "Drivers", "Protected $ Conservative", "Protected $ Expected", "Protected $ Aggressive", "Avg Deficit vs Baseline"])
    grouped = (
        work.groupby(period_col, dropna=False)
        .agg(
            Rows=("movement", "count"),
            Drivers=("driver_name", lambda s: s.astype(str).str.strip().replace("", np.nan).dropna().nunique()),
            protected_conservative=("protected_value_conservative", "sum"),
            protected_expected=("protected_value_expected", "sum"),
            protected_aggressive=("protected_value_aggressive", "sum"),
            avg_deficit_baseline=("deficit_vs_baseline_pct", "mean"),
        )
        .reset_index()
        .rename(columns={
            period_col: label,
            "protected_conservative": "Protected $ Conservative",
            "protected_expected": "Protected $ Expected",
            "protected_aggressive": "Protected $ Aggressive",
            "avg_deficit_baseline": "Avg Deficit vs Baseline",
        })
        .sort_values(label)
    )
    return grouped


def render_executive_rom_mmi_page():
    st.header("Executive ROM/MMI")
    st.caption("Fleet-level rollup of ROM deficit, impairment planning estimates, baseline-protected value, and monthly/quarterly/yearly downloadable reporting.")

    company_name = st.session_state.get("company_name", "")
    df = _load_rom_mmi(company_name)

    if df.empty:
        st.info("No ROM/MMI data found yet. Save rows on Operations → ROM/MMI first.")
        return

    total_rows = len(df)
    drivers_represented = int(df["driver_name"].astype(str).str.strip().replace("", np.nan).dropna().nunique())
    claims_represented = int(df["claim_number"].astype(str).str.strip().replace("", np.nan).dropna().nunique())

    avg_deficit_standard = df["deficit_vs_standard_pct"].dropna().mean() if not df["deficit_vs_standard_pct"].dropna().empty else None
    avg_deficit_baseline = df["deficit_vs_baseline_pct"].dropna().mean() if not df["deficit_vs_baseline_pct"].dropna().empty else None

    protected_conservative = df["protected_value_conservative"].dropna().sum() if not df["protected_value_conservative"].dropna().empty else 0
    protected_expected = df["protected_value_expected"].dropna().sum() if not df["protected_value_expected"].dropna().empty else 0
    protected_aggressive = df["protected_value_aggressive"].dropna().sum() if not df["protected_value_aggressive"].dropna().empty else 0

    latest_dt = pd.to_datetime(df["assessment_date"], errors="coerce").dropna()
    latest_date = latest_dt.max().strftime("%Y-%m-%d") if not latest_dt.empty else "-"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ROM/MMI Rows", total_rows)
    m2.metric("Drivers Represented", drivers_represented)
    m3.metric("Claims Represented", claims_represented)
    m4.metric("Latest Assessment", latest_date)

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Protected Value - Conservative", _fmt_money(protected_conservative))
    m6.metric("Protected Value - Expected", _fmt_money(protected_expected))
    m7.metric("Protected Value - Aggressive", _fmt_money(protected_aggressive))
    m8.metric("Avg Deficit vs Baseline", _fmt_pct(avg_deficit_baseline))

    st.subheader("Time-Based ROM/MMI Rollups")
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

    left, right = st.columns(2)

    with left:
        st.subheader("State Rollup")
        state_rollup = (
            df.groupby("state", dropna=False)
            .agg(
                rows=("state", "size"),
                drivers=("driver_name", lambda s: s.astype(str).str.strip().replace("", np.nan).dropna().nunique()),
                protected_conservative=("protected_value_conservative", "sum"),
                protected_expected=("protected_value_expected", "sum"),
                protected_aggressive=("protected_value_aggressive", "sum"),
            )
            .reset_index()
            .sort_values("protected_expected", ascending=False)
        )
        if not state_rollup.empty:
            state_rollup["protected_conservative"] = state_rollup["protected_conservative"].apply(_fmt_money)
            state_rollup["protected_expected"] = state_rollup["protected_expected"].apply(_fmt_money)
            state_rollup["protected_aggressive"] = state_rollup["protected_aggressive"].apply(_fmt_money)
            state_rollup.columns = [
                "State", "Rows", "Drivers",
                "Protected $ Conservative",
                "Protected $ Expected",
                "Protected $ Aggressive",
            ]
        st.dataframe(state_rollup, use_container_width=True, hide_index=True)

    with right:
        st.subheader("Most Common Body Parts / Movements")
        body_parts = _top_counts(df["body_part"], top_n=6, item_name="Body Part")
        movements = _top_counts(df["movement"], top_n=6, item_name="Movement")
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(body_parts, use_container_width=True, hide_index=True)
        with c2:
            st.dataframe(movements, use_container_width=True, hide_index=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Highest Protected Value Drivers")
        driver_rollup = (
            df.groupby(["driver_name", "driver_id"], dropna=False)
            .agg(
                protected_conservative=("protected_value_conservative", "sum"),
                protected_expected=("protected_value_expected", "sum"),
                protected_aggressive=("protected_value_aggressive", "sum"),
                avg_deficit_vs_baseline=("deficit_vs_baseline_pct", "mean"),
            )
            .reset_index()
            .sort_values("protected_expected", ascending=False)
        )
        if not driver_rollup.empty:
            driver_rollup["Driver"] = driver_rollup.apply(_driver_label, axis=1)
            display_driver = driver_rollup[[
                "Driver", "protected_conservative", "protected_expected", "protected_aggressive", "avg_deficit_vs_baseline"
            ]].head(10).copy()
            display_driver.columns = [
                "Driver", "Protected $ Conservative", "Protected $ Expected", "Protected $ Aggressive", "Avg Deficit vs Baseline"
            ]
            display_driver = _style_rollup(display_driver)
            st.dataframe(display_driver, use_container_width=True, hide_index=True)
        else:
            st.caption("No driver rollup yet.")

    with c4:
        st.subheader("Highest Exposure Claims")
        claim_rollup = (
            df.groupby(["claim_number"], dropna=False)
            .agg(
                driver_name=("driver_name", lambda s: next((x for x in s if _safe_text(x)), "")),
                state=("state", lambda s: next((x for x in s if _safe_text(x)), "")),
                protected_conservative=("protected_value_conservative", "sum"),
                protected_expected=("protected_value_expected", "sum"),
                protected_aggressive=("protected_value_aggressive", "sum"),
            )
            .reset_index()
            .sort_values("protected_expected", ascending=False)
        )
        claim_rollup = claim_rollup[claim_rollup["claim_number"].astype(str).str.strip() != ""]
        if not claim_rollup.empty:
            display_claim = claim_rollup.head(10).copy()
            display_claim.columns = [
                "Claim Number", "Driver", "State",
                "Protected $ Conservative", "Protected $ Expected", "Protected $ Aggressive",
            ]
            display_claim = _style_rollup(display_claim)
            st.dataframe(display_claim, use_container_width=True, hide_index=True)
        else:
            st.caption("No claim rollup yet.")

    st.subheader("Recent ROM/MMI Records")
    recent = df.copy().sort_values("assessment_dt", ascending=False)
    recent_display = recent[[
        "assessment_date", "state", "driver_name", "driver_id", "claim_number", "body_part",
        "movement", "side", "baseline_rom_deg", "post_injury_rom_deg",
        "deficit_vs_baseline_pct", "protected_value_conservative",
        "protected_value_expected", "protected_value_aggressive", "status",
    ]].head(25).copy()

    for col in ["baseline_rom_deg", "post_injury_rom_deg"]:
        recent_display[col] = recent_display[col].apply(lambda x: "-" if pd.isna(x) else (str(int(x)) if float(x).is_integer() else f"{x:.1f}"))
    recent_display["deficit_vs_baseline_pct"] = recent_display["deficit_vs_baseline_pct"].apply(_fmt_pct)
    for col in ["protected_value_conservative", "protected_value_expected", "protected_value_aggressive"]:
        recent_display[col] = recent_display[col].apply(_fmt_money)

    recent_display.columns = [
        "Assessment Date", "State", "Driver", "Driver ID", "Claim Number", "Body Part",
        "Movement", "Side", "Baseline ROM", "Post-Injury ROM", "Deficit vs Baseline",
        "Protected $ Conservative", "Protected $ Expected", "Protected $ Aggressive", "Status",
    ]
    st.dataframe(recent_display, use_container_width=True, hide_index=True)

    summary_df = pd.DataFrame([
        ["ROM/MMI Rows", total_rows],
        ["Drivers Represented", drivers_represented],
        ["Claims Represented", claims_represented],
        ["Protected Value - Conservative", _fmt_money(protected_conservative)],
        ["Protected Value - Expected", _fmt_money(protected_expected)],
        ["Protected Value - Aggressive", _fmt_money(protected_aggressive)],
        ["Avg Deficit vs Standard", _fmt_pct(avg_deficit_standard)],
        ["Avg Deficit vs Baseline", _fmt_pct(avg_deficit_baseline)],
    ], columns=["Metric", "Value"])

    st.subheader("Export PDFs")
    e1, e2, e3 = st.columns(3)
    with e1:
        if st.button("Build Monthly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive ROM/MMI - Monthly", "Executive monthly ROM/MMI report", "Executive ROM/MMI Monthly", company_name, summary_df, _style_rollup(monthly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Monthly PDF", f, file_name="18WW_Executive_ROM_MMI_Monthly.pdf", mime="application/pdf", use_container_width=True)
    with e2:
        if st.button("Build Quarterly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive ROM/MMI - Quarterly", "Executive quarterly ROM/MMI report", "Executive ROM/MMI Quarterly", company_name, summary_df, _style_rollup(quarterly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Quarterly PDF", f, file_name="18WW_Executive_ROM_MMI_Quarterly.pdf", mime="application/pdf", use_container_width=True)
    with e3:
        if st.button("Build Yearly PDF", use_container_width=True):
            pdf_path = _build_pdf("18WW Executive ROM/MMI - Yearly", "Executive yearly ROM/MMI report", "Executive ROM/MMI Yearly", company_name, summary_df, _style_rollup(yearly))
            with open(pdf_path, "rb") as f:
                st.download_button("Download Yearly PDF", f, file_name="18WW_Executive_ROM_MMI_Yearly.pdf", mime="application/pdf", use_container_width=True)

    st.markdown(
        f"""
        <div style="background:{BRAND_SILVER}; border:1px solid #d7ddea; border-radius:14px; padding:16px; margin-top:12px;">
            <div style="font-weight:700; color:{BRAND_NAVY}; margin-bottom:6px;">Executive Use</div>
            <div style="color:{BRAND_SLATE};">
                This page estimates how much claim value may be protected by having pre-injury ROM baselines.
                Conservative, expected, and aggressive bands are launch-model planning estimates for executive use.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
