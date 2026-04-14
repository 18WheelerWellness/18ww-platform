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
    c1.metric("Driver", claim.get("driver_name", ""))
    c2.metric("Lag Days", claim.get("lag_days", 0))
    c3.metric("RTW Days", claim.get("actual_rtw_days", 0))

    st.markdown("---")

    # -----------------------------
    # RTW ASSIGNMENT
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
    # COST IMPACT (CLOSE SECTION)
    # ----------------
