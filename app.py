def show_company_overview(company_name, drivers_df, claims_df):
    st.title(company_name)

    num_drivers = len(drivers_df) if isinstance(drivers_df, pd.DataFrame) else 0
    active_claims = 0

    if isinstance(claims_df, pd.DataFrame) and "current_status" in claims_df.columns:
        active_claims = len(claims_df[claims_df["current_status"] != "Completed"])

    st.subheader(f"{num_drivers} Drivers | {active_claims} Active Claims")

    st.markdown("---")

    rtw_ratio = "N/A"
    avg_rtw_days = "N/A"
    lag_time = "N/A"
    total_cost = "N/A"

    if isinstance(claims_df, pd.DataFrame) and not claims_df.empty:

        if "days_injury_to_rtw" in claims_df.columns:
            valid_rtw = claims_df["days_injury_to_rtw"].dropna()
            if len(valid_rtw) > 0:
                fast = valid_rtw[valid_rtw <= 4]
                rtw_ratio = f"{round(len(fast) / len(valid_rtw) * 100, 1)}%"
                avg_rtw_days = f"{round(valid_rtw.mean(), 1)}"

        if "lag_days" in claims_df.columns:
            valid_lag = claims_df["lag_days"].dropna()
            if len(valid_lag) > 0:
                lag_time = f"{round(valid_lag.mean(), 1)}"

        if "total_cost" in claims_df.columns:
            cost = pd.to_numeric(claims_df["total_cost"], errors="coerce").dropna()
            if len(cost) > 0:
                total_cost = f"${int(cost.sum()):,}"

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("RTW Ratio (≤4 Days)", rtw_ratio)
    col2.metric("Avg RTW Days", avg_rtw_days)
    col3.metric("Lag Time (Days)", lag_time)
    col4.metric("Total Claim Cost", total_cost)

    st.markdown("---")

    st.markdown("**Lag time and delayed return-to-work are the primary drivers of claim cost.**")
    st.markdown("➡️ Let’s look at where this is happening inside your claims.")
