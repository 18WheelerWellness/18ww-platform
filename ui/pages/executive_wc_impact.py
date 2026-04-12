import os
from io import BytesIO

import streamlit as st


def render_executive_wc_impact():
    st.header("Executive WC Financial Impact")

    st.write(
        "Executive financial view of workers' comp cost, premium drag, savings, and revenue pressure using data already loaded in the app."
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
    def get_wc_source_data():
        data = {}

        if "exec_wc_company_name" in st.session_state:
            data["company_name"] = st.session_state.get("exec_wc_company_name")

        if "exec_wc_incurred_losses" in st.session_state:
            data["incurred_losses"] = float(st.session_state.get("exec_wc_incurred_losses", 0.0))

        if "exec_wc_total_fte" in st.session_state:
            data["total_fte"] = float(st.session_state.get("exec_wc_total_fte", 0.0))

        if "exec_wc_cost_label" in st.session_state:
            data["cost_label"] = st.session_state.get("exec_wc_cost_label")

        if "exec_wc_cost_value" in st.session_state:
            data["cost_value"] = float(st.session_state.get("exec_wc_cost_value", 0.0))

        if "exec_wc_accident_cost" in st.session_state:
            data["accident_cost"] = float(st.session_state.get("exec_wc_accident_cost", 0.0))

        if "exec_wc_profit_margin_percent" in st.session_state:
            data["profit_margin_percent"] = float(st.session_state.get("exec_wc_profit_margin_percent", 0.0))

        if "exec_wc_sales_needed" in st.session_state:
            data["sales_needed_for_accident"] = float(st.session_state.get("exec_wc_sales_needed", 0.0))

        if "exec_wc_controllable_premium" in st.session_state:
            data["controllable_premium"] = float(st.session_state.get("exec_wc_controllable_premium", 0.0))

        if "exec_wc_current_mod" in st.session_state:
            data["current_mod"] = float(st.session_state.get("exec_wc_current_mod", 0.0))

        if "exec_wc_minimum_mod" in st.session_state:
            data["minimum_mod"] = float(st.session_state.get("exec_wc_minimum_mod", 0.0))

        if "exec_wc_avoidable_premium" in st.session_state:
            data["avoidable_premium"] = float(st.session_state.get("exec_wc_avoidable_premium", 0.0))

        if "exec_wc_savings_to_date" in st.session_state:
            data["savings_to_date"] = float(st.session_state.get("exec_wc_savings_to_date", 0.0))

        if "exec_rtw_fi_target_days" in st.session_state:
            data["rtw_target_days"] = float(st.session_state.get("exec_rtw_fi_target_days", 0.0))

        if "exec_rtw_fi_cost_per_lost_day" in st.session_state:
            data["rtw_cost_per_day"] = float(st.session_state.get("exec_rtw_fi_cost_per_lost_day", 0.0))

        if "exec_rtw_fi_profit_margin_percent" in st.session_state:
            data["rtw_profit_margin"] = float(st.session_state.get("exec_rtw_fi_profit_margin_percent", 0.0))

        if "exec_rtw_fi_avoidable_lost_days" in st.session_state:
            data["avoidable_lost_days"] = float(st.session_state.get("exec_rtw_fi_avoidable_lost_days", 0.0))

        if "exec_rtw_fi_financial_drag" in st.session_state:
            data["financial_drag"] = float(st.session_state.get("exec_rtw_fi_financial_drag", 0.0))

        if "exec_rtw_fi_sales_needed" in st.session_state:
            data["sales_needed_for_drag"] = float(st.session_state.get("exec_rtw_fi_sales_needed", 0.0))

        return data

    
    def build_pdf_bytes(
        company_label,
        incurred_losses,
        cost_per_employee,
        accident_cost,
        sales_needed_for_accident,
        controllable_premium,
        current_mod,
        minimum_mod,
        avoidable_premium,
        savings_to_date,
        financial_drag,
        sales_needed_for_drag,
        total_impact,
        executive_readout,
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
            fontSize=26,
            leading=28,
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

        story.append(Paragraph("Executive WC Financial Impact", title_center))
        story.append(Paragraph(company_label, subtitle_center))
        story.append(Spacer(1, 8))

        headline = Table(
            [
                [Paragraph("TOTAL EXECUTIVE IMPACT", label_style)],
                [Paragraph(fmt_money(total_impact), giant_number)],
                [Paragraph("Combined executive view of premium drag, RTW drag, and savings.", body_style)],
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
                    [[Paragraph("Incurred Losses", label_style)],
                     [Paragraph(fmt_money(incurred_losses), value_style)]],
                    colWidths=[3.5 * inch]
                ),
                Table(
                    [[Paragraph("Cost / Employee", label_style)],
                     [Paragraph(fmt_money(cost_per_employee), value_style)]],
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
                    [[Paragraph("Savings to Date", label_style)],
                     [Paragraph(fmt_money(savings_to_date), value_style)]],
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

        money_table = Table(
            [
                ["Executive Financial Signal", "Value"],
                ["Accident Cost", fmt_money(accident_cost)],
                ["Sales Needed for Accident", fmt_money(sales_needed_for_accident)],
                ["Controllable Premium", fmt_money(controllable_premium)],
                ["Current Mod", f"{current_mod:.2f}"],
                ["Minimum Mod", f"{minimum_mod:.2f}"],
                ["RTW Financial Drag", fmt_money(financial_drag)],
                ["Sales Needed for RTW Drag", fmt_money(sales_needed_for_drag)],
            ],
            colWidths=[3.8 * inch, 2.8 * inch],
        )
        money_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF1F2")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#F1B5BC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF8F8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ])
        )
        story.append(money_table)
        story.append(Spacer(1, 8))

        story.append(Paragraph(executive_readout, body_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Prepared with 18WW impact analysis tools.", footer_style))

        doc.build(story)
        return buffer.getvalue()

    data = get_wc_source_data()

    if not data:
        st.warning(
            "No WC financial source data found in app memory yet. "
            "First load data in Workers' Comp Financial Impact and RTW Financial Impact."
        )
        return

    st.markdown("---")
    st.subheader("Data Source Status")

    a, b, c = st.columns(3)

    with a:
        st.success("WC Financial Impact data loaded") if "company_name" in data else st.info("WC Financial Impact data not loaded")

    with b:
        st.success("RTW Financial data loaded") if "rtw_ratio_df" in data else st.info("RTW Financial data not loaded")

    with c:
        st.success("Savings / premium inputs loaded") if "savings_to_date" in data else st.info("Savings / premium inputs not loaded")

    company_label = data.get("company_name", "Selected Company")
    incurred_losses = float(data.get("incurred_losses", 0.0))
    total_fte = float(data.get("total_fte", 0.0))
    accident_cost = float(data.get("accident_cost", 0.0))
    profit_margin_percent = float(data.get("profit_margin_percent", 0.0))
    controllable_premium = float(data.get("controllable_premium", 0.0))
    current_mod = float(data.get("current_mod", 0.0))
    minimum_mod = float(data.get("minimum_mod", 0.0))
    savings_to_date = float(data.get("savings_to_date", 0.0))

    # Cost / employee from WC page
    cost_per_employee = float(data.get("cost_value", 0.0))
    cost_label = data.get("cost_label", "Cost / Employee")

    # Premium drag
    avoidable_premium = (
        controllable_premium * (current_mod - minimum_mod)
        if current_mod >= minimum_mod else 0.0
    )

    # Sales needed to cover accident / premium style pressure
    sales_needed_for_accident = (
        accident_cost / (profit_margin_percent / 100)
        if profit_margin_percent > 0 else 0.0
    )

    # RTW drag derived from RTW data + assumptions if present
    rtw_df = data.get("rtw_ratio_df")
    target_days = float(data.get("rtw_target_days", 4.0))
    cost_per_lost_day = float(data.get("rtw_cost_per_day", 350.0))
    rtw_profit_margin = float(data.get("rtw_profit_margin", profit_margin_percent if profit_margin_percent > 0 else 5.0))

    financial_drag = 0.0
    avoidable_lost_days = 0.0

    if rtw_df is not None and not rtw_df.empty:
        work = rtw_df.copy()
        if "injury_date" in work.columns:
            work["injury_date"] = st.session_state["rtw_ratio_df"]["injury_date"] if "injury_date" in st.session_state["rtw_ratio_df"] else work["injury_date"]
        if "rtw_days" not in work.columns:
            if "injury_date" in work.columns and "rtw_date" in work.columns:
                work["injury_date"] = pd.to_datetime(work["injury_date"], errors="coerce")
                work["rtw_date"] = pd.to_datetime(work["rtw_date"], errors="coerce")
                work["rtw_days"] = (work["rtw_date"] - work["injury_date"]).dt.days

        if "rtw_days" in work.columns:
            work = work.dropna(subset=["rtw_days"]).copy()
            work["rtw_days"] = work["rtw_days"].clip(lower=0)
            work["avoidable_days"] = (work["rtw_days"] - target_days).clip(lower=0)
            avoidable_lost_days = float(work["avoidable_days"].sum())
            financial_drag = avoidable_lost_days * cost_per_lost_day

    sales_needed_for_drag = (
        financial_drag / (rtw_profit_margin / 100)
        if rtw_profit_margin > 0 else 0.0
    )

    total_impact = avoidable_premium + financial_drag + savings_to_date

    st.markdown("---")
    st.subheader("Executive Financial Snapshot")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_kpi_card("Incurred Losses", fmt_money(incurred_losses), "#f8fafc", "#6b7280")
    with c2:
        render_kpi_card(cost_label, fmt_money(cost_per_employee), "#eef4ff", "#2563eb")
    with c3:
        render_kpi_card("Avoidable Premium", fmt_money(avoidable_premium), "#fff1f2", "#dc2626")
    with c4:
        render_kpi_card("Savings to Date", fmt_money(savings_to_date), "#ecfdf3", "#16a34a")

    st.subheader("Executive Pressure Signals")

    d1, d2, d3, d4 = st.columns(4)

    with d1:
        render_kpi_card("Accident Cost", fmt_money(accident_cost), "#f8fafc", "#6b7280")
    with d2:
        render_kpi_card("Sales Needed for Accident", fmt_money(sales_needed_for_accident), "#fff7ed", "#ea580c")
    with d3:
        render_kpi_card("RTW Financial Drag", fmt_money(financial_drag), "#fff1f2", "#dc2626")
    with d4:
        render_kpi_card("Sales Needed for RTW Drag", fmt_money(sales_needed_for_drag), "#fff7ed", "#ea580c")

    st.markdown("---")
    st.subheader("Executive Inputs")

    e1, e2, e3, e4 = st.columns(4)

    with e1:
        st.metric("Controllable Premium", fmt_money(controllable_premium))
    with e2:
        st.metric("Current Mod", f"{current_mod:.2f}")
    with e3:
        st.metric("Minimum Mod", f"{minimum_mod:.2f}")
    with e4:
        st.metric("Profit Margin", f"{profit_margin_percent:.1f}%")

    st.markdown("---")
    st.subheader("Executive Readout")

    executive_readout = (
        f"For **{company_label}**, the operation is carrying **{fmt_money(avoidable_premium)}** in avoidable premium, "
        f"**{fmt_money(financial_drag)}** in estimated RTW financial drag, and has already documented "
        f"**{fmt_money(savings_to_date)}** in savings to date. "
        f"At current assumptions, that represents a combined executive impact view of **{fmt_money(total_impact)}**."
    )

    st.write(executive_readout)

    st.markdown(
        f"""
        <div style="
            background-color:#eef4ff;
            border-left:6px solid #2563eb;
            padding:14px;
            border-radius:10px;
            margin-bottom:15px;
        ">
        <b>Executive Money Story:</b><br>
        Avoidable premium and RTW drag together create direct financial pressure,
        while low margins turn that pressure into larger required sales volume.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if avoidable_premium > 0 and financial_drag > 0:
        st.warning("Executive signal: premium drag and RTW drag are both active cost drivers.")
    elif avoidable_premium > 0 or financial_drag > 0:
        st.info("Executive signal: one major drag source is active, but there is still measurable opportunity.")
    else:
        st.success("Executive signal: direct premium and RTW drag appear controlled under current assumptions.")

    st.markdown("---")
    st.subheader("PDF Export")

    pdf_bytes = build_pdf_bytes(
        company_label=company_label,
        incurred_losses=incurred_losses,
        cost_per_employee=cost_per_employee,
        accident_cost=accident_cost,
        sales_needed_for_accident=sales_needed_for_accident,
        controllable_premium=controllable_premium,
        current_mod=current_mod,
        minimum_mod=minimum_mod,
        avoidable_premium=avoidable_premium,
        savings_to_date=savings_to_date,
        financial_drag=financial_drag,
        sales_needed_for_drag=sales_needed_for_drag,
        total_impact=total_impact,
        executive_readout=executive_readout,
    )

    if pdf_bytes is None:
        st.warning("PDF export needs reportlab installed. Run: pip install reportlab")
    else:
        safe_name = company_label.lower().replace(" ", "_")
        st.download_button(
            label="Download Executive WC Financial Impact PDF",
            data=pdf_bytes,
            file_name=f"{safe_name}_executive_wc_financial_impact.pdf",
            mime="application/pdf",
            key="executive_wc_financial_impact_pdf_download",
        )