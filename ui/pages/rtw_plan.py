import streamlit as st
import pandas as pd

def show_rtw_plan():
    st.header("Return-to-Work (RTW)")

    df = st.session_state.get("claims_cleaned_df", pd.DataFrame())

    if df.empty:
        st.warning("No claims available.")
        return

    # -----------------------------
    # SELECT CLAIM
    # -----------------------------
    claim_number = st.selectbox("Select Claim", df["claim_number"])

    claim = df[df["claim_number"] == claim_number].iloc[0]

    # -----------------------------
    # CLAIM SNAPSHOT
    # -----------------------------
    st.subheader("Claim Snapshot")

    c1, c2, c3 = st.columns(3)
    c1.metric("Driver", claim["driver_name"])
    c2.metric("Lag Days", claim["lag_days"])
    c3.metric("RTW Days", claim["actual_rtw_days"])

    st.markdown("---")

    # -----------------------------
    # RTW PROCESS
    # -----------------------------
    st.subheader("RTW Assignment")

    tier = st.selectbox(
        "RTW Tier",
        ["A – Seated", "B – Light Duty", "C – Walk/Stand", "D – Lower Body", "E – Upper Body", "J – No Driving"]
    )

    job = st.selectbox(
        "Temporary Job",
        ["Safety Review", "Training Support", "Admin Work", "Scheduling", "Custom"]
    )

    if job == "Custom":
        job = st.text_input("Enter Custom Job")

    rtw_date = st.text_input("RTW Start Date (Target: 3–5 days)")

    st.markdown("---")

    # -----------------------------
    # COST IMPACT (CLOSE DRIVER)
    # -----------------------------
    lag = pd.to_numeric(claim.get("lag_days", 0), errors="coerce")
    cost_per_day = pd.to_numeric(claim.get("cost_per_day", 0), errors="coerce")

    if pd.notna(rtw_days) and pd.notna(cost_per_day):

        # CURRENT = what they are doing now
        current_cost = rtw_days * cost_per_day

        # IMPROVED = your system
        improved_days = 5
        improved_cost = improved_days * cost_per_day

        savings = current_cost - improved_cost

        st.subheader("Cost Impact")

        col1, col2 = st.columns(2)

        # LEFT = GOOD (future)
        col1.metric(
        "With RTW System",
        f"${int(improved_cost):,}",
        f"-{int(savings):,} vs current"
        )

        # RIGHT = CURRENT (pain)
        col2.metric(
            "Current Cost",
            f"${int(current_cost):,}"
        )

        st.success(f"Estimated Savings: ${int(savings):,}")
        st.success("Reducing time out of work directly reduces claim cost.")

    # -----------------------------
    # SAVE
    # -----------------------------
        if st.button("Save RTW Plan"):
            st.success("RTW plan saved.")
