import streamlit as st
import pandas as pd

def show_rtw_plan():

    st.title("Return-to-Work (RTW) Impact")

    df = st.session_state.get("claims_cleaned_df", pd.DataFrame())

    if df.empty:
        st.warning("No claims data available.")
        return

    df = df.copy()

    df["lag_days"] = pd.to_numeric(df["lag_days"], errors="coerce").fillna(0)
    df["actual_rtw_days"] = pd.to_numeric(df["actual_rtw_days"], errors="coerce").fillna(0)
    df["cost_per_day"] = pd.to_numeric(df.get("cost_per_day", 250), errors="coerce").fillna(250)

    df["total_cost"] = df["actual_rtw_days"] * df["cost_per_day"]

    # -----------------------------
    # SUMMARY
    # -----------------------------
    total_cost = int(df["total_cost"].sum())
    avg_rtw = round(df["actual_rtw_days"].mean(), 1)

    st.metric("Total Cost", f"${total_cost:,}")
    st.metric("Avg RTW Days", avg_rtw)

    st.markdown("---")

    # -----------------------------
    # FLAG PROBLEMS
    # -----------------------------
    st.subheader("Claims Driving Cost")

    df["flag"] = df["actual_rtw_days"].apply(
        lambda x: "🔴 High Cost" if x > 10 else "🟡 Moderate" if x > 5 else "🟢 Controlled"
    )

    st.dataframe(df[[
        "claim_number",
        "driver_name",
        "lag_days",
        "actual_rtw_days",
        "total_cost",
        "flag"
    ]])

    st.markdown("---")

    # -----------------------------
    # VALUE LINE
    # -----------------------------
    st.markdown(
        "Each additional day out of work increases claim cost. Reducing RTW time directly lowers total spend."
    )
