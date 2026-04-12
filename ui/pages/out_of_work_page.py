import os
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


OOW_CREDENTIALS_PATH = "credentials/18ww_google_service_account.json"
OOW_TEST_SHEET_ID = "1fnSGKqatQlyl5ZIeHHx66Bsud4SCX4wDa32ma73RsW0"
OOW_TEST_TAB_NAME = "Employees Out of Work"
OOW_LOCAL_CSV_PATH = "data/employees_out_of_work.csv"


def render_out_of_work_page():
    st.header("Employees Out of Work")

    st.write(
        "Track employees currently out of work, long-duration open claims, and open claim duration trends."
    )

    def classify_open_bucket(days):
        if days <= 7:
            return "0-7 Days"
        if days <= 30:
            return "8-30 Days"
        if days <= 90:
            return "31-90 Days"
        if days <= 180:
            return "91-180 Days"
        if days <= 365:
            return "181-365 Days"
        return "365+ Days"

    def render_kpi_card(label, value, bg_color, border_color, help_text=None):
        extra = f'<div style="font-size:13px;color:#444;margin-top:6px;">{help_text}</div>' if help_text else ""
        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                border-left: 8px solid {border_color};
                padding: 18px 20px;
                border-radius: 12px;
                margin-bottom: 12px;
                box-shadow: 0 1px 6px rgba(0,0,0,0.08);
            ">
                <div style="font-size:14px;font-weight:600;color:#444;margin-bottom:8px;">
                    {label}
                </div>
                <div style="font-size:30px;font-weight:700;color:#111;">
                    {value}
                </div>
                {extra}
            </div>
            """,
            unsafe_allow_html=True
        )

    def build_pdf_bytes(
        selected_company,
        selected_period,
        selected_division,
        open_claims_count,
        out_6_months_count,
        avg_open_days,
        median_open_days,
        out_6_months_rate,
        bucket_counts,
    ):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                Image,
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            return None

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.4 * inch,
            bottomMargin=0.4 * inch,
        )

        styles = getSampleStyleSheet()

        title_center = ParagraphStyle(
            "title_center",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=22,
            alignment=1,
            textColor=colors.HexColor("#163A6B"),
            spaceAfter=4,
        )

        subtitle_center = ParagraphStyle(
            "subtitle_center",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=1,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=4,
        )

        body_style = ParagraphStyle(
            "body_style",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#222222"),
            spaceAfter=4,
        )

        footer_style = ParagraphStyle(
            "footer_style",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            alignment=1,
        )

        story = []

        try:
            logo_path = os.path.join("assets", "18ww_logo.png")
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=95, height=95)
                logo_table = Table([[logo]], colWidths=[7.1 * inch])
                logo_table.setStyle(
                    TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ])
                )
                story.append(logo_table)
        except Exception:
            pass

        banner = Table(
            [[Paragraph("18WW", title_center)]],
            colWidths=[7.1 * inch],
        )
        banner.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#163A6B")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(banner)
        story.append(Spacer(1, 8))

        story.append(Paragraph("Employees Out of Work Report", title_center))
        story.append(Paragraph(selected_company, subtitle_center))
        story.append(
            Paragraph(
                f"Period: {selected_period} | Division: {selected_division}",
                subtitle_center,
            )
        )
        story.append(Spacer(1, 8))

        headline = Table(
            [[Paragraph(f"<b>Out of Work Now</b><br/><font size=20>{open_claims_count}</font>", title_center)]],
            colWidths=[7.1 * inch],
        )
        headline.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF4FF")),
                ("BOX", (0, 0), (-1, -1), 1.4, colors.HexColor("#2563EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ])
        )
        story.append(headline)
        story.append(Spacer(1, 8))

        summary_table = Table(
            [
                ["Metric", "Value"],
                ["Employees Out of Work", f"{open_claims_count}"],
                ["Out 6+ Months", f"{out_6_months_count}"],
                ["Average Open Days", f"{avg_open_days:.1f}"],
                ["Median Open Days", f"{median_open_days:.1f}"],
                ["Out 6+ Months Rate", f"{out_6_months_rate:.1f}%"],
            ],
            colWidths=[3.6 * inch, 3.0 * inch],
        )
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE7F7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 10))

        bucket_table_data = [["Open Duration Bucket", "Claim Count"]]
        for bucket, count in bucket_counts.items():
            bucket_table_data.append([bucket, str(int(count))])

        bucket_table = Table(bucket_table_data, colWidths=[3.6 * inch, 3.0 * inch])
        bucket_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECFDF3")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7E7D1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FCF8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ])
        )
        story.append(bucket_table)
        story.append(Spacer(1, 8))

        story.append(
            Paragraph(
                f"This selection currently has <b>{open_claims_count}</b> employees out of work. "
                f"<b>{out_6_months_count}</b> have been out for 6+ months, representing <b>{out_6_months_rate:.1f}%</b> of open claims. "
                f"Long-duration open claims can drive reserve pressure, attorney risk, and operational drag.",
                body_style,
            )
        )
        story.append(Spacer(1, 6))
        story.append(Paragraph("Prepared with 18WW impact analysis tools.", footer_style))

        doc.build(story)
        return buffer.getvalue()

    def load_source_df():
        source_message = ""
        source_warning = ""
        source_df = pd.DataFrame()

        try:
            from utils.google_sheets_sync import GoogleSheetsSync

            if os.path.exists(OOW_CREDENTIALS_PATH):
                try:
                    sheets = GoogleSheetsSync(
                        credentials_path=OOW_CREDENTIALS_PATH,
                        workbook_ids={"operations": OOW_TEST_SHEET_ID},
                    )

                    source_df = sheets.read_tab("operations", OOW_TEST_TAB_NAME)

                    if not source_df.empty:
                        source_message = f"Loaded company list from Google Sheets tab: {OOW_TEST_TAB_NAME}"
                    elif os.path.exists(OOW_LOCAL_CSV_PATH):
                        source_df = pd.read_csv(OOW_LOCAL_CSV_PATH)
                        source_warning = f"Google Sheets tab was empty, so local CSV fallback was used: {OOW_LOCAL_CSV_PATH}"
                    else:
                        source_warning = "Google Sheets tab was empty and no local CSV fallback was found."
                except Exception as e:
                    if os.path.exists(OOW_LOCAL_CSV_PATH):
                        source_df = pd.read_csv(OOW_LOCAL_CSV_PATH)
                        source_warning = f"Google Sheets could not be read, so local CSV fallback was used. Error: {e}"
                    else:
                        source_warning = f"Google Sheets could not be read and no local CSV fallback was found. Error: {e}"
            elif os.path.exists(OOW_LOCAL_CSV_PATH):
                source_df = pd.read_csv(OOW_LOCAL_CSV_PATH)
                source_warning = f"Credentials file not found, so local CSV fallback was used: {OOW_LOCAL_CSV_PATH}"
            else:
                source_warning = "No Google Sheets credentials file and no local CSV fallback were found."
        except Exception as e:
            if os.path.exists(OOW_LOCAL_CSV_PATH):
                source_df = pd.read_csv(OOW_LOCAL_CSV_PATH)
                source_warning = f"Google Sheets sync is not ready, so local CSV fallback was used. Error: {e}"
            else:
                source_warning = f"Google Sheets sync is not ready and no local CSV fallback was found. Error: {e}"

        return source_df, source_message, source_warning

    st.markdown("---")
    st.subheader("Data Source")

    if st.button("Reload from Google Sheets / Local CSV", key="out_of_work_reload_source"):
        for key in [
            "out_of_work_source_df",
            "out_of_work_source_message",
            "out_of_work_source_warning",
            "oow_company",
        ]:
            st.session_state.pop(key, None)
        st.rerun()

    uploaded_file = st.file_uploader(
        "Upload Out of Work CSV",
        type=["csv"],
        key="out_of_work_upload",
    )

    if "out_of_work_source_df" not in st.session_state:
        source_df, source_message, source_warning = load_source_df()
        st.session_state["out_of_work_source_df"] = source_df
        st.session_state["out_of_work_source_message"] = source_message
        st.session_state["out_of_work_source_warning"] = source_warning

    source_df = st.session_state.get("out_of_work_source_df", pd.DataFrame())
    source_message = st.session_state.get("out_of_work_source_message", "")
    source_warning = st.session_state.get("out_of_work_source_warning", "")

    if source_message:
        st.success(source_message)

    if source_warning:
        st.info(source_warning)

    if uploaded_file is not None:
        try:
            source_df = pd.read_csv(uploaded_file)
            st.session_state["out_of_work_source_df"] = source_df
            st.success("Uploaded CSV loaded.")
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
            return

    if source_df.empty:
        st.error("No data found in Google Sheets or local CSV.")
        return

    df = source_df.copy()

    required_cols = [
        "company",
        "period",
        "division",
        "claim_id",
        "injury_date",
        "status",
        "snapshot_date",
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        return

    df["injury_date"] = pd.to_datetime(df["injury_date"], errors="coerce")
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")

    bad_dates = df["injury_date"].isna() | df["snapshot_date"].isna()
    if bad_dates.any():
        st.warning("Some rows had invalid dates and were removed.")
        df = df.loc[~bad_dates].copy()

    if df.empty:
        st.error("No valid rows left after date cleanup.")
        return

    df["status"] = df["status"].astype(str).str.strip()
    df["open_days"] = (df["snapshot_date"] - df["injury_date"]).dt.days
    df["open_days"] = df["open_days"].clip(lower=0)

    st.session_state["out_of_work_df"] = df.copy()

    st.markdown("---")
    st.subheader("Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        company_options = ["All"] + sorted(df["company"].dropna().astype(str).unique().tolist())
        selected_company = st.selectbox("Company", company_options, key="oow_company")

    with col2:
        period_options = ["All"] + sorted(df["period"].dropna().astype(str).unique().tolist())
        selected_period = st.selectbox("Period", period_options, key="oow_period")

    with col3:
        division_options = ["All"] + sorted(df["division"].dropna().astype(str).unique().tolist())
        selected_division = st.selectbox("Division", division_options, key="oow_division")

    filtered = df.copy()

    if selected_company != "All":
        filtered = filtered[filtered["company"].astype(str) == selected_company]
    if selected_period != "All":
        filtered = filtered[filtered["period"].astype(str) == selected_period]
    if selected_division != "All":
        filtered = filtered[filtered["division"].astype(str) == selected_division]

    if filtered.empty:
        st.warning("No rows match the selected filters.")
        return

    open_filtered = filtered[filtered["status"].str.lower() == "out"].copy()

    if open_filtered.empty:
        st.info("No employees currently out of work for the selected filters.")
        return

    open_filtered["open_bucket"] = open_filtered["open_days"].apply(classify_open_bucket)

    open_claims_count = len(open_filtered)
    out_6_months_count = (open_filtered["open_days"] > 180).sum()
    avg_open_days = open_filtered["open_days"].mean()
    median_open_days = open_filtered["open_days"].median()
    out_6_months_rate = (out_6_months_count / open_claims_count) * 100 if open_claims_count > 0 else 0.0

    st.markdown("---")
    st.subheader("Out of Work Summary")

    a, b = st.columns(2)
    c, d = st.columns(2)

    with a:
        render_kpi_card("Employees Out of Work", f"{open_claims_count}", "#eef4ff", "#2563eb")
    with b:
        render_kpi_card("Out 6+ Months", f"{out_6_months_count}", "#fff1f2", "#dc2626")
    with c:
        render_kpi_card("Average Open Days", f"{avg_open_days:.1f}", "#f8fafc", "#6b7280")
    with d:
        render_kpi_card("Out 6+ Months Rate", f"{out_6_months_rate:.1f}%", "#fff7ed", "#ea580c")

    st.markdown("---")
    st.subheader("Out of Work Story")

    st.write(
        f"This selection has **{open_claims_count} employees currently out of work**. "
        f"**{out_6_months_count}** have been out more than 6 months, with an average open duration of **{avg_open_days:.1f} days**."
    )

    if out_6_months_rate <= 10:
        st.success("Long-duration exposure is relatively controlled.")
    elif out_6_months_rate <= 25:
        st.info("There is moderate long-duration exposure. This should be monitored closely.")
    else:
        st.warning("Long-duration exposure is elevated. These claims can drive significant operational and financial drag.")

    st.markdown("---")
    st.subheader("Open Duration Chart")

    bucket_order = ["0-7 Days", "8-30 Days", "31-90 Days", "91-180 Days", "181-365 Days", "365+ Days"]
    bucket_counts = (
        open_filtered["open_bucket"]
        .value_counts()
        .reindex(bucket_order, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(bucket_counts.index, bucket_counts.values)
    ax.set_title("Employees Out of Work by Duration")
    ax.set_ylabel("Open Claim Count")
    ax.set_xlabel("Open Duration Bucket")
    plt.xticks(rotation=20)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("---")
    st.subheader("Open Claims by Period")

    trend_df = (
        open_filtered.groupby("period", dropna=False)["open_days"]
        .mean()
        .reset_index()
        .sort_values("period")
    )

    if len(trend_df) > 1:
        fig2, ax2 = plt.subplots(figsize=(9, 4.5))
        ax2.plot(trend_df["period"].astype(str), trend_df["open_days"], marker="o")
        ax2.set_title("Average Open Days by Period")
        ax2.set_ylabel("Average Open Days")
        ax2.set_xlabel("Period")
        plt.xticks(rotation=20)
        plt.tight_layout()
        st.pyplot(fig2)
    else:
        st.info("Need more than one period in the filtered data to show an open-days trend line.")

    st.markdown("---")
    st.subheader("Detail Table")

    detail_cols = [
        "company",
        "period",
        "division",
        "claim_id",
        "injury_date",
        "snapshot_date",
        "status",
        "open_days",
        "open_bucket",
    ]

    detail_view = open_filtered[detail_cols].copy()
    detail_view["injury_date"] = detail_view["injury_date"].dt.strftime("%Y-%m-%d")
    detail_view["snapshot_date"] = detail_view["snapshot_date"].dt.strftime("%Y-%m-%d")

    st.dataframe(detail_view, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("PDF Export")

    company_label = selected_company if selected_company != "All" else "All Companies"
    period_label = selected_period if selected_period != "All" else "All Periods"
    division_label = selected_division if selected_division != "All" else "All Divisions"

    pdf_bytes = build_pdf_bytes(
        selected_company=company_label,
        selected_period=period_label,
        selected_division=division_label,
        open_claims_count=open_claims_count,
        out_6_months_count=out_6_months_count,
        avg_open_days=avg_open_days,
        median_open_days=median_open_days,
        out_6_months_rate=out_6_months_rate,
        bucket_counts=bucket_counts,
    )

    if pdf_bytes is None:
        st.warning("PDF export needs reportlab installed. Run: pip install reportlab")
    else:
        safe_name = company_label.lower().replace(" ", "_")
        st.download_button(
            label="Download Out of Work PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}_out_of_work_report.pdf",
            mime="application/pdf",
            key="out_of_work_pdf_download",
        )