import streamlit as st
import pandas as pd

def render_executive_overview():

    st.title("Executive Overview")

    df = st.session_state.get("claims_cleaned_df", pd.DataFrame())

    if df.empty:
        st.warning("No claims data available.")
        return

    df = df.copy()

    df["lag_days"] = pd.to_numeric(df["lag_days"], errors="coerce").fillna(0)
    df["actual_rtw_days"] = pd.to_numeric(df["actual_rtw_days"], errors="coerce").fillna(0)
    df["cost_per_day"] = pd.to_numeric(df.get("cost_per_day", 250), errors="coerce").fillna(250)

    df["total_cost"] = df["actual_rtw_days"] * df["cost_per_day"]

    total_cost = int(df["total_cost"].sum())
    avg_lag = round(df["lag_days"].mean(), 1)
    avg_rtw = round(df["actual_rtw_days"].mean(), 1)

    # 🎯 TARGETS
    target_rtw = 5
    target_lag = 1

    improved_cost = int((df["cost_per_day"] * target_rtw).sum())
    savings = total_cost - improved_cost
    improvement_pct = round((savings / total_cost) * 100, 1) if total_cost > 0 else 0

    # -----------------------------
    # TOP METRICS
    # -----------------------------
    st.subheader("Current vs Target")

    c1, c2, c3 = st.columns(3)

    c1.metric("Avg Lag Days", avg_lag, f"{avg_lag - target_lag:+}")
    c2.metric("Avg RTW Days", avg_rtw, f"{avg_rtw - target_rtw:+}")
    c3.metric("Total Cost", f"${total_cost:,}")

    st.markdown("---")

    # -----------------------------
    # DECISION BLOCK
    # -----------------------------
    st.subheader("Financial Opportunity")

    o1, o2 = st.columns(2)

    o1.metric("Current Cost", f"${total_cost:,}")
    o2.metric("With RTW System", f"${improved_cost:,}")

    if savings > 0:
        st.success(f"💰 Estimated Savings: ${savings:,} ({improvement_pct}%)")
    else:
        st.warning("No savings opportunity detected")

    st.markdown("---")

    # -----------------------------
    # VISUAL (SIMPLE BAR)
    # -----------------------------
    chart_df = pd.DataFrame({
        "Scenario": ["Current", "Optimized"],
        "Cost": [total_cost, improved_cost]
    })

    st.bar_chart(chart_df.set_index("Scenario"))

    # -----------------------------
    # CLOSE LINE
    # -----------------------------
    st.markdown(
        "Reducing lag time and return-to-work delays directly lowers claim costs and premium exposure."
    )
