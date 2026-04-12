import os
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


LAG_CREDENTIALS_PATH = "credentials/18ww_google_service_account.json"
LAG_TEST_SHEET_ID = "1fnSGKqatQlyl5ZIeHHx66Bsud4SCX4wDa32ma73RsW0"
LAG_TEST_TAB_NAME = "Lag Time"
LAG_LOCAL_CSV_PATH = "data/lag_time.csv"


def render_lag_time_page():
    st.header("Lag Time")

    st.write(
        "Track how quickly injuries are reported and visualize lag-time performance by company, period, and division."
    )

    def classify_lag_bucket(days):
        if days <= 0:
            return "Same Day"
        if days <= 1:
            return "1 Day"
        if days <= 3:
            return "2-3 Days"
        if days <= 7:
            return "4-7 Days"
        if days <= 14:
            return "8-14 Days"
        if days <= 28:
            return "15-28 Days"
        return "29+ Days"

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
        total_claims,
        avg_lag,
        median_lag,
        same_day_rate,
        within_3_days_rate,
        after_7_days_rate,
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

        story.append(Paragraph("Lag Time Report", title_center))
        story.append(Paragraph(selected_company, subtitle_center))
        story.append(
            Paragraph(
                f"Period: {selected_period} | Division: {selected_division}",
                subtitle_center,
            )
        )
        story.append(Spacer(1, 8))

        headline = Table(
            [[Paragraph(f"<b>Average Lag Time</b><br/><font size=20>{avg_lag:.1f} days</font>", title_center)]],
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
                ["Claims Count", f"{total_claims}"],
                ["Average Lag Time", f"{avg_lag:.1f} days"],
                ["Median Lag Time", f"{median_lag:.1f} days"],
                ["Same-Day Reporting", f"{same_day_rate:.1f}%"],
                ["Reported Within 3 Days", f"{within_3_days_rate:.1f}%"],
                ["Reported After 7 Days", f"{after_7_days_rate:.1f}%"],
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

        bucket_table_data = [["Lag Bucket", "Claim Count"]]
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
                f"This selection includes {total_claims} claims. "
                f"Average lag time is <b>{avg_lag:.1f} days</b>, with <b>{same_day_rate:.1f}%</b> reported the same day "
                f"and <b>{after_7_days_rate:.1f}%</b> reported after 7 days. "
                f"Elevated lag time can increase claim cost, complexity, and attorney risk.",
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

            if os.path.exists(LAG_CREDENTIALS_PATH):
                try:
                    sheets = GoogleSheetsSync(
                        credentials_path=LAG_CREDENTIALS_PATH,
                        workbook_ids={"operations": LAG_TEST_SHEET_ID},
                    )

                    source_df = sheets.read_tab("operations", LAG_TEST_TAB_NAME)

                    if not source_df.empty:
                        source_message = f"Loaded company list from Google Sheets tab: {LAG_TEST_TAB_NAME}"
                    elif os.path.exists(LAG_LOCAL_CSV_PATH):
                        source_df = pd.read_csv(LAG_LOCAL_CSV_PATH)
                        source_warning = f"Google Sheets tab was empty, so local CSV fallback was used: {LAG_LOCAL_CSV_PATH}"
                    else:
                        source_warning = "Google Sheets tab was empty and no local CSV fallback was found."
                except Exception as e:
                    if os.path.exists(LAG_LOCAL_CSV_PATH):
                        source_df = pd.read_csv(LAG_LOCAL_CSV_PATH)
                        source_warning = f"Google Sheets could not be read, so local CSV fallback was used. Error: {e}"
                    else:
                        source_warning = f"Google Sheets could not be read and no local CSV fallback was found. Error: {e}"
            elif os.path.exists(LAG_LOCAL_CSV_PATH):
                source_df = pd.read_csv(LAG_LOCAL_CSV_PATH)
                source_warning = f"Credentials file not found, so local CSV fallback was used: {LAG_LOCAL_CSV_PATH}"
            else:
                source_warning = "No Google Sheets credentials file and no local CSV fallback were found."
        except Exception as e:
            if os.path.exists(LAG_LOCAL_CSV_PATH):
                source_df = pd.read_csv(LAG_LOCAL_CSV_PATH)
                source_warning = f"Google Sheets sync is not ready, so local CSV fallback was used. Error: {e}"
            else:
                source_warning = f"Google Sheets sync is not ready and no local CSV fallback was found. Error: {e}"

        return source_df, source_message, source_warning

    st.markdown("---")
    st.subheader("Data Source")

    if st.button("Reload from Google Sheets / Local CSV", key="lag_reload_source"):
        for key in [
            "lag_source_df",
            "lag_source_message",
            "lag_source_warning",
            "lag_company",
        ]:
            st.session_state.pop(key, None)
        st.rerun()

    uploaded_file = st.file_uploader(
        "Upload Lag Time CSV",
        type=["csv"],
        key="lag_time_upload",
    )

    if "lag_source_df" not in st.session_state:
        source_df, source_message, source_warning = load_source_df()
        st.session_state["lag_source_df"] = source_df
        st.session_state["lag_source_message"] = source_message
        st.session_state["lag_source_warning"] = source_warning

    source_df = st.session_state.get("lag_source_df", pd.DataFrame())
    source_message = st.session_state.get("lag_source_message", "")
    source_warning = st.session_state.get("lag_source_warning", "")

    if source_message:
        st.success(source_message)

    if source_warning:
        st.info(source_warning)

    if uploaded_file is not None:
        try:
            source_df = pd.read_csv(uploaded_file)
            st.session_state["lag_source_df"] = source_df
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
        "report_date",
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        return

    df["injury_date"] = pd.to_datetime(df["injury_date"], errors="coerce")
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")

    bad_dates = df["injury_date"].isna() | df["report_date"].isna()
    if bad_dates.any():
        st.warning("Some rows had invalid dates and were removed.")
        df = df.loc[~bad_dates].copy()

    if df.empty:
        st.error("No valid rows left after date cleanup.")
        return

    df["lag_days"] = (df["report_date"] - df["injury_date"]).dt.days
    df["lag_days"] = df["lag_days"].clip(lower=0)
    df["lag_bucket"] = df["lag_days"].apply(classify_lag_bucket)

    st.session_state["lag_time_df"] = df.copy()

    st.markdown("---")
    st.subheader("Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        company_options = ["All"] + sorted(df["company"].dropna().astype(str).unique().tolist())
        selected_company = st.selectbox("Company", company_options, key="lag_company")

    with col2:
        period_options = ["All"] + sorted(df["period"].dropna().astype(str).unique().tolist())
        selected_period = st.selectbox("Period", period_options, key="lag_period")

    with col3:
        division_options = ["All"] + sorted(df["division"].dropna().astype(str).unique().tolist())
        selected_division = st.selectbox("Division", division_options, key="lag_division")

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

    total_claims = len(filtered)
    avg_lag = filtered["lag_days"].mean()
    median_lag = filtered["lag_days"].median()
    same_day_rate = (filtered["lag_days"] == 0).mean() * 100
    within_3_days_rate = (filtered["lag_days"] <= 3).mean() * 100
    after_7_days_rate = (filtered["lag_days"] > 7).mean() * 100

    st.markdown("---")
    st.subheader("Lag Time Summary")

    a, b = st.columns(2)
    c, d = st.columns(2)
    e, f = st.columns(2)

    with a:
        render_kpi_card("Average Lag Time", f"{avg_lag:.1f} days", "#eef4ff", "#2563eb")
    with b:
        render_kpi_card("Median Lag Time", f"{median_lag:.1f} days", "#f8fafc", "#6b7280")
    with c:
        render_kpi_card("Same-Day Reporting", f"{same_day_rate:.1f}%", "#ecfdf3", "#16a34a")
    with d:
        render_kpi_card("Reported Within 3 Days", f"{within_3_days_rate:.1f}%", "#ecfdf3", "#16a34a")
    with e:
        render_kpi_card("Reported After 7 Days", f"{after_7_days_rate:.1f}%", "#fff1f2", "#dc2626")
    with f:
        render_kpi_card("Claims Count", f"{total_claims}", "#fff7ed", "#ea580c")

    st.markdown("---")
    st.subheader("Lag Time Story")

    st.write(
        f"This selection has **{total_claims} claims** with an average lag time of **{avg_lag:.1f} days**. "
        f"**{same_day_rate:.1f}%** were reported the same day, while **{after_7_days_rate:.1f}%** were reported after 7 days."
    )

    if avg_lag <= 1:
        st.success("Lag time is very strong. Reporting speed is helping reduce downstream claim friction.")
    elif avg_lag <= 3:
        st.info("Lag time is decent, but there is still room to improve early reporting discipline.")
    else:
        st.warning("Lag time is elevated. This can increase claim cost, complexity, and attorney risk over time.")

    st.markdown("---")
    st.subheader("Lag Bucket Chart")

    bucket_order = ["Same Day", "1 Day", "2-3 Days", "4-7 Days", "8-14 Days", "15-28 Days", "29+ Days"]
    bucket_counts = (
        filtered["lag_bucket"]
        .value_counts()
        .reindex(bucket_order, fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(bucket_counts.index, bucket_counts.values)
    ax.set_title("Lag Time Distribution")
    ax.set_ylabel("Claim Count")
    ax.set_xlabel("Lag Bucket")
    plt.xticks(rotation=20)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("---")
    st.subheader("Lag Trend by Period")

    trend_df = (
        filtered.groupby("period", dropna=False)["lag_days"]
        .mean()
        .reset_index()
        .sort_values("period")
    )

    if len(trend_df) > 1:
        fig2, ax2 = plt.subplots(figsize=(9, 4.5))
        ax2.plot(trend_df["period"].astype(str), trend_df["lag_days"], marker="o")
        ax2.set_title("Average Lag Time by Period")
        ax2.set_ylabel("Average Lag Days")
        ax2.set_xlabel("Period")
        plt.xticks(rotation=20)
        plt.tight_layout()
        st.pyplot(fig2)
    else:
        st.info("Need more than one period in the filtered data to show a lag trend line.")

    st.markdown("---")
    st.subheader("Detail Table")

    detail_cols = [
        "company",
        "period",
        "division",
        "claim_id",
        "injury_date",
        "report_date",
        "lag_days",
        "lag_bucket",
    ]

    detail_view = filtered[detail_cols].copy()
    detail_view["injury_date"] = detail_view["injury_date"].dt.strftime("%Y-%m-%d")
    detail_view["report_date"] = detail_view["report_date"].dt.strftime("%Y-%m-%d")

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
        total_claims=total_claims,
        avg_lag=avg_lag,
        median_lag=median_lag,
        same_day_rate=same_day_rate,
        within_3_days_rate=within_3_days_rate,
        after_7_days_rate=after_7_days_rate,
        bucket_counts=bucket_counts,
    )

    if pdf_bytes is None:
        st.warning("PDF export needs reportlab installed. Run: pip install reportlab")
    else:
        safe_name = company_label.lower().replace(" ", "_")
        st.download_button(
            label="Download Lag Time PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}_lag_time_report.pdf",
            mime="application/pdf",
            key="lag_time_pdf_download",
        )
