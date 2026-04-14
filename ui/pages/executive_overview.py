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
