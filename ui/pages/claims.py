import streamlit as st
import pandas as pd

def show_claims():
    st.header("Claims")

    df = st.session_state.get("claims_cleaned_df", pd.DataFrame())

    if df.empty:
        st.warning("No claims found.")
        return

    # -----------------------------
    # CLEAN DATA
    # -----------------------------
    df["lag_days"] = pd.to_numeric(df.get("lag_days", 0), errors="coerce")
    df["actual_rtw_days"] = pd.to_numeric(df.get("actual_rtw_days", 0), errors="coerce")
    df["cost_per_day"] = pd.to_numeric(df.get("cost_per_day", 0), errors="coerce")

    # -----------------------------
    # TOP METRICS (PAIN)
    # -----------------------------
    st.subheader("Claims Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Claims", len(df))
    col2.metric("Avg Lag Days", round(df["lag_days"].mean(), 1))
    col3.metric("Avg RTW Days", round(df["actual_rtw_days"].mean(), 1))

    total_cost = (df["actual_rtw_days"] * df["cost_per_day"]).sum()
    col4.metric("Estimated Cost", f"${int(total_cost):,}")

    st.markdown("**Lag time and delayed return-to-work are the biggest drivers of claim cost.**")

    st.markdown("---")

    # -----------------------------
    # CLAIMS TABLE
    # -----------------------------
    st.subheader("Claims Detail")

    display_cols = [
        "claim_number",
        "driver_name",
        "lag_days",
        "actual_rtw_days",
        "claim_status"
    ]

    existing_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(df[existing_cols], use_container_width=True)
