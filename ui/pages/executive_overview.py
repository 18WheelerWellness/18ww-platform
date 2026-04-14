import streamlit as st
from io import BytesIO


def render_executive_overview():
    st.header("Executive Overview")

    # -----------------------------
    # LOAD DATA FROM SESSION
    # -----------------------------
    company_label = st.session_state.get("exec_wc_company_name", "Selected Company")

    avoidable_premium = float(st.session_state.get("exec_wc_avoidable_premium", 0.0))
    financial_drag = float(st.session_state.get("exec_rtw_fi_financial_drag", 0.0))
    savings_to_date = float(st.session_state.get("exec_wc_savings_to_date", 0.0))

    rtw_ratio = st.session_state.get("exec_rtw_fi_rtw_ratio")
    avg_lag = st.session_state.get("exec_avg_lag_days")
    employees_out = st.session_state.get("exec_employees_out")

    total_pressure = avoidable_premium + financial_drag
    total_relief = savings_to_date
    master_opportunity = total_pressure + total_relief

    # -----------------------------
    # HEADLINE (THIS CLOSES)
    # -----------------------------
    st.markdown("### Total Financial Opportunity")

    st.metric(
        "Total Opportunity",
        f"${master_opportunity:,.0f}"
    )

    st.markdown("**This combines workers' comp pressure and recoverable savings.**")

    st.markdown("---")

    # -----------------------------
    # PRESSURE (PROBLEM)
    # -----------------------------
    st.subheader("Current Financial Pressure")

    p1, p2 = st.columns(2)

    with p1:
        st.metric("Avoidable Premium", f"${avoidable_premium:,.0f}")

    with p2:
        st.metric("RTW Financial Drag", f"${financial_drag:,.0f}")

    st.markdown("---")

    # -----------------------------
    # RELIEF (SOLUTION)
    # -----------------------------
    st.subheader("Recoverable Savings")

    st.metric("Savings to Date", f"${total_relief:,.0f}")

    st.markdown("---")

    # -----------------------------
    # OPERATIONS (WHY THIS IS HAPPENING)
    # -----------------------------
    st.subheader("Operational Drivers")

    o1, o2, o3 = st.columns(3)

    with o1:
        st.metric(
            "RTW Ratio (0–4 Days)",
            f"{rtw_ratio:.1f}%" if rtw_ratio is not None else "N/A"
        )

    with o2:

                st.metric(
            "Average Lag Time",
            f"{avg_lag:.1f}" if avg_lag is not None else "N/A"
        )

    with o3:
        st.metric(
            "Employees Out",
            f"{employees_out}" if employees_out is not None else "N/A"
        )

    st.markdown("---")

    # -----------------------------
    # EXECUTIVE SUMMARY
    # -----------------------------
    st.subheader("Executive Summary")

    st.markdown(f"""
- **Current pressure:** ${total_pressure:,.0f}  
- **Recoverable savings:** ${total_relief:,.0f}  
- **Total opportunity:** ${master_opportunity:,.0f}  

👉 The biggest drivers are **lag time and delayed return-to-work**  
👉 Improving RTW speed directly reduces **claim cost and premium impact**
""")

    # -----------------------------
    # SIGNAL (CLOSE)
    # -----------------------------
    if total_pressure > total_relief:
        st.error("⚠️ Current system is losing more than it’s recovering.")
    elif total_pressure > 0:
        st.warning("⚠️ System is improving but still has financial drag.")
    else:
        st.success("✅ System appears controlled.")

    st.markdown("---")

    # -----------------------------
    # SIMPLE PDF EXPORT (SAFE)
    # -----------------------------
    st.subheader("Export")

    def simple_pdf():
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            return None

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        story = []
        story.append(Paragraph(f"Executive Overview - {company_label}", styles["Title"]))
        story.append(Paragraph(f"Total Opportunity: ${master_opportunity:,.0f}", styles["Heading2"]))
        story.append(Paragraph(f"Total Pressure: ${total_pressure:,.0f}", styles["Normal"]))
        story.append(Paragraph(f"Recoverable Savings: ${total_relief:,.0f}", styles["Normal"]))

        doc.build(story)
        return buffer.getvalue()

    pdf_bytes = simple_pdf()

    if pdf_bytes:
        st.download_button(
            "Download Executive PDF",
            data=pdf_bytes,
            file_name="executive_overview.pdf",
            mime="application/pdf"
        )
