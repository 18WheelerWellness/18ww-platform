import streamlit as st
import pandas as pd
from io_layer.google_company_store import load_company_rows_from_shared_tab

CLAIMS_TAB_NAME = "claims"


def show_claims():
    st.header("Claims")

    company_name = st.session_state.get("company_name", "")

    # -----------------------------
    # LOAD DATA (quietly)
    # -----------------------------
    try:
        df = load_company_rows_from_shared_tab(company_name, CLAIMS_TAB_NAME)
        if df is None:
            df = pd.DataFrame()
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        st.info("No claims found for this company.")
        return

    claims_df = df.copy()

    # -----------------------------
    # CLEAN KEY FIELDS
    # -----------------------------
    for col in ["lag_days", "actual_rtw_days", "cost_per_day"]:
        if col not in claims_df.columns:
            claims_df[col] = 0

    claims_df["lag_days"] = pd.to_numeric(claims_df["lag_days"], errors="coerce")
    claims_df["actual_rtw_days"] = pd.to_numeric(claims_df["actual_rtw_days"], errors="coerce")
    claims_df["cost_per_day"] = pd.to_numeric(claims_df["cost_per_day"], errors="coerce")

    # -----------------------------
    # SUMMARY (TOP PRIORITY)
    # -----------------------------
    st.subheader("Claims Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Claims", len(claims_df))

    with col2:
        open_claims = claims_df["claim_status"].astype(str).str.contains(
            "open|active|pending", case=False, na=False
        ).sum() if "claim_status" in claims_df.columns else 0
        st.metric("Open Claims", int(open_claims))

    with col3:
        avg_lag = round(claims_df["lag_days"].mean(), 1) if claims_df["lag_days"].notna().any() else 0
        st.metric("Avg Lag Days", avg_lag)

    with col4:
        avg_rtw = round(claims_df["actual_rtw_days"].mean(), 1) if claims_df["actual_rtw_days"].notna().any() else 0
        st.metric("Avg RTW Days", avg_rtw)

    # -----------------------------
    # PROBLEM CALLOUT
    # -----------------------------
    st.markdown("---")
    st.markdown("**Most claim cost comes from delays in reporting and delayed return-to-work.**")

    # -----------------------------
    # SIMPLE COST VIEW (HIGH IMPACT)
    # -----------------------------
    if "cost_per_day" in claims_df.columns:
        claims_df["estimated_cost"] = claims_df["actual_rtw_days"] * claims_df["cost_per_day"]

        total_cost = claims_df
