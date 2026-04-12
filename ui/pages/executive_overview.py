import os
from io import BytesIO

import streamlit as st


def render_executive_overview():
    st.header("Executive Overview")

    st.write(
        "Master executive view combining RTW performance and workers' comp financial impact into one decision page."
    )

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
            unsafe_allow_html=True,
        )

    def fmt_money(x):
        return f"${x:,.2f}"

    def build_pdf_bytes(
        company_label,
        cost_label,
        cost_value,
        avoidable_premium,
        savings_to_date,
        accident_sales_needed,
        rtw_ratio,
        avg_lag,
        employees_out,
        claims_6_months,
        financial_drag,
        drag_sales_needed,
        total_pressure,
        total_relief,
        master_opportunity,
        readout_text,
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
            rightMargin=0.45 * inch,
            leftMargin=0.45 * inch,
            topMargin=0.35 * inch,
            bottomMargin=0.35 * inch,
        )

        styles = getSampleStyleSheet()

        title_center = ParagraphStyle(
            "title_center",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=24,
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

        giant_number = ParagraphStyle(
            "giant_number",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=30,
            alignment=1,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
        )

        label_style = ParagraphStyle(
            "label_style",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=1,
            textColor=colors.HexColor("#475569"),
            spaceAfter=2,
        )

        value_style = ParagraphStyle(
            "value_style",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=17,
            alignment=1,
            textColor=colors.HexColor("#111827"),
            spaceAfter=2,
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

        story.append(Paragraph("Executive Overview", title_center))
        story.append(Paragraph(company_label, subtitle_center))
        story.append(Spacer(1, 8))

        headline = Table(
            [
                [Paragraph("MASTER OPPORTUNITY", label_style)],
                [Paragraph(fmt_money(master_opportunity), giant_number)],
                [Paragraph("Combined executive view of pressure, drag, and documented savings.", body_style)],
            ],
            colWidths=[7.1 * inch],
        )
        headline.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF4FF")),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#2563EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        story.append(headline)
        story.append(Spacer(1, 8))

        top_cards = [
            [
                Table(
                    [[Paragraph("RTW Ratio (0-4 Days)", label_style)],
                     [Paragraph(f"{rtw_ratio:.1f}%" if rtw_ratio is not None else "N/A", value_style)]],
                    colWidths=[3.5 * inch]
                ),
                Table(
                    [[Paragraph(cost_label, label_style)],
                     [Paragraph(fmt_money(cost_value), value_style)]],
                    colWidths=[3.5 * inch]
                ),
            ],
            [
                Table(
                    [[Paragraph("Avoidable Premium", label_style)],
                     [Paragraph(fmt_money(avoidable_premium), value_style)]],
                    colWidths=[3.5 * inch]
                ),
                Table(
                    [[Paragraph("RTW Financial Drag", label_style)],
                     [Paragraph(fmt_money(financial_drag), value_style)]],
                    colWidths=[3.5 * inch]
                ),
            ],
        ]

        for row in top_cards:
            for card in row:
                card.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ])
                )

        story.append(
            Table(
                top_cards,
                colWidths=[3.55 * inch, 3.55 * inch],
                style=TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]),
            )
        )
        story.append(Spacer(1, 8))

        summary_table = Table(
            [
                ["Executive Signal", "Value"],
                ["Average Lag Time", f"{avg_lag:.1f}" if avg_lag is not None else "N/A"],
                ["Employees Out of Work", str(int(employees_out)) if employees_out is not None else "N/A"],
                ["6+ Month Claims", str(int(claims_6_months)) if claims_6_months is not None else "N/A"],
                ["Sales Needed for Accident", fmt_money(accident_sales_needed)],
                ["Sales Needed for RTW Drag", fmt_money(drag_sales_needed)],
                ["Savings to Date", fmt_money(savings_to_date)],
                ["Total Pressure", fmt_money(total_pressure)],
                ["Total Relief", fmt_money(total_relief)],
            ],
            colWidths=[3.8 * inch, 2.8 * inch],
        )
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECFDF3")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7E7D1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FCF8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 8))

        story.append(Paragraph(readout_text, body_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Prepared with 18WW impact analysis tools.", footer_style))

        doc.build(story)
        return buffer.getvalue()

    # Pull RTW executive memory
    rtw_ratio = st.session_state.get("exec_rtw_fi_rtw_ratio")
    avg_rtw_days = st.session_state.get("exec_rtw_fi_avg_rtw_days")
    avg_lag = None
    employees_out = None
    claims_6_months = None

    if "lag_time_df" in st.session_state:
        lag_df = st.session_state["lag_time_df"].copy()
        if "lag_days" in lag_df.columns:
            avg_lag = float(lag_df["lag_days"].dropna().mean()) if not lag_df["lag_days"].dropna().empty else None
        elif "injury_date" in lag_df.columns and "report_date" in lag_df.columns:
            import pandas as pd
            lag_df["injury_date"] = pd.to_datetime(lag_df["injury_date"], errors="coerce")
            lag_df["report_date"] = pd.to_datetime(lag_df["report_date"], errors="coerce")
            lag_df["lag_days"] = (lag_df["report_date"] - lag_df["injury_date"]).dt.days.clip(lower=0)
            avg_lag = float(lag_df["lag_days"].dropna().mean()) if not lag_df["lag_days"].dropna().empty else None

    if "out_of_work_df" in st.session_state:
        out_df = st.session_state["out_of_work_df"].copy()
        if "status" in out_df.columns:
            out_df["status"] = out_df["status"].astype(str).str.strip().str.lower()
            out_df = out_df[out_df["status"] == "out"].copy()
        if "open_days" in out_df.columns:
            employees_out = len(out_df)
            claims_6_months = int((out_df["open_days"] > 180).sum())
        elif "injury_date" in out_df.columns and "snapshot_date" in out_df.columns:
            import pandas as pd
            out_df["injury_date"] = pd.to_datetime(out_df["injury_date"], errors="coerce")
            out_df["snapshot_date"] = pd.to_datetime(out_df["snapshot_date"], errors="coerce")
            out_df["open_days"] = (out_df["snapshot_date"] - out_df["injury_date"]).dt.days.clip(lower=0)
            employees_out = len(out_df)
            claims_6_months = int((out_df["open_days"] > 180).sum())

    # Pull WC executive memory
    company_label = st.session_state.get("exec_wc_company_name", "Selected Company")
    cost_label = st.session_state.get("exec_wc_cost_label", "Cost / Employee")
    cost_value = float(st.session_state.get("exec_wc_cost_value", 0.0))
    incurred_losses = float(st.session_state.get("exec_wc_incurred_losses", 0.0))
    accident_cost = float(st.session_state.get("exec_wc_accident_cost", 0.0))
    accident_sales_needed = float(st.session_state.get("exec_wc_sales_needed", 0.0))
    avoidable_premium = float(st.session_state.get("exec_wc_avoidable_premium", 0.0))
    savings_to_date = float(st.session_state.get("exec_wc_savings_to_date", 0.0))
    controllable_premium = float(st.session_state.get("exec_wc_controllable_premium", 0.0))
    current_mod = float(st.session_state.get("exec_wc_current_mod", 0.0))
    minimum_mod = float(st.session_state.get("exec_wc_minimum_mod", 0.0))

    # Pull RTW financial memory
    financial_drag = float(st.session_state.get("exec_rtw_fi_financial_drag", 0.0))
    drag_sales_needed = float(st.session_state.get("exec_rtw_fi_sales_needed", 0.0))

    any_loaded = any([
        "exec_wc_company_name" in st.session_state,
        "exec_wc_avoidable_premium" in st.session_state,
        "exec_rtw_fi_financial_drag" in st.session_state,
        "exec_rtw_fi_rtw_ratio" in st.session_state,
        "lag_time_df" in st.session_state,
        "out_of_work_df" in st.session_state,
    ])

    if not any_loaded:
        st.warning(
            "No executive overview source data found in app memory yet. "
            "First load Workers' Comp Financial Impact, RTW Financial Impact, Lag Time, and Employees Out of Work."
        )
        return

    total_pressure = avoidable_premium + financial_drag
    total_relief = savings_to_date
    master_opportunity = total_pressure + total_relief

    st.markdown("---")
    st.subheader("Data Source Status")

    a, b, c = st.columns(3)
    with a:
        st.success("WC executive data loaded") if "exec_wc_company_name" in st.session_state else st.info("WC executive data not loaded")
    with b:
        st.success("RTW executive data loaded") if "exec_rtw_fi_rtw_ratio" in st.session_state else st.info("RTW executive data not loaded")
    with c:
        ok = ("lag_time_df" in st.session_state) or ("out_of_work_df" in st.session_state)
        st.success("Operational RTW data loaded") if ok else st.info("Operational RTW data not loaded")

    st.markdown("---")
    st.subheader("Master Executive Snapshot")

    d1, d2, d3, d4 = st.columns(4)

    with d1:
        render_kpi_card(
            "Master Opportunity",
            fmt_money(master_opportunity),
            "#eef4ff",
            "#2563eb",
        )
    with d2:
        render_kpi_card(
            "Total Pressure",
            fmt_money(total_pressure),
            "#fff1f2",
            "#dc2626",
        )
    with d3:
        render_kpi_card(
            "Total Relief",
            fmt_money(total_relief),
            "#ecfdf3",
            "#16a34a",
        )
    with d4:
        render_kpi_card(
            "RTW Ratio (0-4 Days)",
            f"{rtw_ratio:.1f}%" if rtw_ratio is not None else "N/A",
            "#f8fafc",
            "#6b7280",
        )

    st.subheader("Executive Operations")

    e1, e2, e3, e4 = st.columns(4)

    with e1:
        render_kpi_card(
            cost_label,
            fmt_money(cost_value),
            "#eef4ff",
            "#2563eb",
        )
    with e2:
        render_kpi_card(
            "Average Lag Time",
            f"{avg_lag:.1f}" if avg_lag is not None else "N/A",
            "#f8fafc",
            "#6b7280",
        )
    with e3:
        render_kpi_card(
            "Employees Out of Work",
            f"{employees_out}" if employees_out is not None else "N/A",
            "#fff7ed",
            "#ea580c",
        )
    with e4:
        render_kpi_card(
            "6+ Month Claims",
            f"{claims_6_months}" if claims_6_months is not None else "N/A",
            "#fff1f2",
            "#dc2626",
        )

    st.subheader("Executive Financial Pressure")

    f1, f2, f3, f4 = st.columns(4)

    with f1:
        render_kpi_card(
            "Avoidable Premium",
            fmt_money(avoidable_premium),
            "#fff1f2",
            "#dc2626",
        )
    with f2:
        render_kpi_card(
            "RTW Financial Drag",
            fmt_money(financial_drag),
            "#fff1f2",
            "#dc2626",
        )
    with f3:
        render_kpi_card(
            "Sales Needed for Accident",
            fmt_money(accident_sales_needed),
            "#fff7ed",
            "#ea580c",
        )
    with f4:
        render_kpi_card(
            "Sales Needed for RTW Drag",
            fmt_money(drag_sales_needed),
            "#fff7ed",
            "#ea580c",
        )

    st.markdown("---")
    st.subheader("Executive Readout")

    readout_text = (
        f"For **{company_label}**, the current executive picture shows **{fmt_money(avoidable_premium)}** in avoidable premium "
        f"and **{fmt_money(financial_drag)}** in RTW financial drag, creating **{fmt_money(total_pressure)}** in combined pressure. "
        f"The operation has also documented **{fmt_money(savings_to_date)}** in savings to date, bringing the full executive opportunity view to "
        f"**{fmt_money(master_opportunity)}**. "
    )

    if rtw_ratio is not None:
        readout_text += f"RTW ratio is **{rtw_ratio:.1f}%** within 0-4 days. "
    if avg_lag is not None:
        readout_text += f"Lag time averages **{avg_lag:.1f} days**. "
    if employees_out is not None:
        readout_text += f"There are currently **{employees_out}** employees out of work"
        if claims_6_months is not None:
            readout_text += f", including **{claims_6_months}** open 6+ months"
        readout_text += "."

    st.write(readout_text)

    if total_pressure > total_relief:
        st.warning("Executive signal: current pressure is outweighing documented relief. This is a strong intervention opportunity.")
    elif total_pressure > 0:
        st.info("Executive signal: the system is producing savings, but drag sources are still active.")
    else:
        st.success("Executive signal: direct executive pressure appears controlled under current assumptions.")

    st.markdown(
        f"""
        <div style="
            background-color:#eef4ff;
            border-left:6px solid #2563eb;
            padding:14px;
            border-radius:10px;
            margin-bottom:15px;
        ">
        <b>Boardroom Story:</b><br>
        This page combines workers' comp financial pressure, RTW system drag, and documented savings into one leadership view.
        It is designed to show both what is hurting the operation and what 18WW can help recover.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("PDF Export")

    pdf_bytes = build_pdf_bytes(
        company_label=company_label,
        cost_label=cost_label,
        cost_value=cost_value,
        avoidable_premium=avoidable_premium,
        savings_to_date=savings_to_date,
        accident_sales_needed=accident_sales_needed,
        rtw_ratio=rtw_ratio,
        avg_lag=avg_lag,
        employees_out=employees_out,
        claims_6_months=claims_6_months,
        financial_drag=financial_drag,
        drag_sales_needed=drag_sales_needed,
        total_pressure=total_pressure,
        total_relief=total_relief,
        master_opportunity=master_opportunity,
        readout_text=readout_text,
    )

    if pdf_bytes is None:
        st.warning("PDF export needs reportlab installed. Run: pip install reportlab")
    else:
        safe_name = company_label.lower().replace(" ", "_")
        st.download_button(
            label="Download Executive Overview PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}_executive_overview.pdf",
            mime="application/pdf",
            key="executive_overview_pdf_download",
        )