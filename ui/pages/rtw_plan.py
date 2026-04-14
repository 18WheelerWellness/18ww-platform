import streamlit as st
import pandas as pd
from io_layer.google_company_store import load_company_rows_from_shared_tab, save_company_rows_to_shared_tab

TAB_NAME = "rtw_plan"

def show_rtw_plan():
    st.header("Return-to-Work (RTW) Plan")

    company_name = st.session_state.get("company_name", "")

    # -----------------------------
    # LOAD CLAIMS
    # -----------------------------
    claims_df = load_company_rows_from_shared_tab(company_name, "claims")

    if claims_df is None or claims_df.empty:
        st.warning("No claims found.")
        return

    claim_numbers = claims_df["claim_number"].dropna().astype(str).unique().tolist()
    selected_claim = st.selectbox("Select Claim", claim_numbers)

    claim_row = claims_df[claims_df["claim_number"].astype(str) == selected_claim].iloc[0]

    # -----------------------------
    # CLAIM SNAPSHOT (KEEP)
    # -----------------------------
    st.subheader("Claim Snapshot")

    c1, c2, c3 = st.columns(3)
    c1.metric("Driver", claim_row.get("driver_name", ""))
    c2.metric("Injury Area", claim_row.get("injury_area", ""))
    c3.metric("Claim Stage", claim_row.get("claim_stage", ""))

    st.markdown("---")

    # -----------------------------
    # CORE PROCESS (THIS IS THE SELL)
    # -----------------------------
    st.subheader("RTW Process")

    st.markdown("""
    **Step 1: Receive Work Ability**  
    **Step 2: Assign RTW Tier (based on restrictions)**  
    **Step 3: Place into temporary job**  
    **Step 4: Start RTW within 3–5 days**
    """)

    # -----------------------------
    # RTW TIER (CORE DIFFERENTIATOR)
    # -----------------------------
    st.subheader("Assign RTW Tier")

    TIER_OPTIONS = [
        "A – Seated / One-Hand Light Duty",
        "B – Seated/Standing, Keyboard OK",
        "C – Walk/Stand Light",
        "D – Lower Extremity Protected",
        "E – Upper Extremity Protected",
        "J – No CMV Driving",
    ]

    tier = st.selectbox("RTW Tier", TIER_OPTIONS)

    TIER_RESTRICTIONS = {
        "A – Seated / One-Hand Light Duty": "Seated work, no lifting, no driving",
        "B – Seated/Standing, Keyboard OK": "Light duty, no heavy lifting",
        "C – Walk/Stand Light": "Light walking, no uneven ground",
        "D – Lower Extremity Protected": "Limit walking/standing",
        "E – Upper Extremity Protected": "No heavy arm use",
        "J – No CMV Driving": "No driving, admin work only",
    }

    st.info(TIER_RESTRICTIONS.get(tier, ""))

    # -----------------------------
    # JOB ASSIGNMENT
    # -----------------------------
    st.subheader("Temporary Job Assignment")

    job = st.selectbox(
        "Select Job",
        [
            "Training documentation",
            "Safety review",
            "ELDT compliance tasks",
            "Scheduling support",
            "Custom job",
        ],
    )

    custom_job = ""
    if job == "Custom job":
        custom_job = st.text_input("Enter Custom Job")

    final_job = custom_job if job == "Custom job" else job

    # -----------------------------
    # RTW DATE (MONEY DRIVER)
    # -----------------------------
    st.subheader("Return-to-Work Start")

    rtw_start_date = st.text_input("RTW Start Date (Target: within 3–5 days)")

    # -----------------------------
    # COST IMPACT (THIS CLOSES)
    # -----------------------------
    lag_days = pd.to_numeric(claim_row.get("lag_days", 0), errors="coerce")
    cost_per_day = pd.to_numeric(claim_row)
