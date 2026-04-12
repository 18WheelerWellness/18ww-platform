import streamlit as st
import pandas as pd
from analytics.merge_utils import get_merged_driver_rom_claims


def context_matches_filters(selected_company, selected_terminal):
    rtw_company = st.session_state.get("rtw_selected_company", "All")
    rtw_terminal = st.session_state.get("rtw_selected_terminal", "All")

    company_match = (
        rtw_company == "All"
        or selected_company == "All"
        or rtw_company == selected_company
    )

    terminal_match = (
        rtw_terminal == "All"
        or selected_terminal == "All"
        or rtw_terminal == selected_terminal
    )

    return company_match and terminal_match


def show_savings():
    st.header("Savings")
    st.write("Estimate prevention, RTW, and premium-impact opportunity from current filtered data.")

    merged_df = get_merged_driver_rom_claims()

    if merged_df is None:
        st.info("Load driver and ROM data first so the app can build merged data automatically.")
        return

    merged_df = merged_df.copy()

    if "driver_id" in merged_df.columns:
        merged_df["driver_id"] = merged_df["driver_id"].astype(str)

    if "total_cost" in merged_df.columns:
        merged_df["total_cost_numeric"] = pd.to_numeric(
            merged_df["total_cost"], errors="coerce"
        ).fillna(0)
    else:
        merged_df["total_cost_numeric"] = 0.0

    if "lost_time_days" in merged_df.columns:
        merged_df["lost_time_days_numeric"] = pd.to_numeric(
            merged_df["lost_time_days"], errors="coerce"
        ).fillna(0)
    else:
        merged_df["lost_time_days_numeric"] = 0.0

    st.subheader("Savings Filters")

    company_options = ["All"]
    if "company" in merged_df.columns:
        company_options += sorted(merged_df["company"].dropna().astype(str).unique().tolist())

    terminal_options = ["All"]
    if "terminal" in merged_df.columns:
        terminal_options += sorted(merged_df["terminal"].dropna().astype(str).unique().tolist())

    risk_options = ["All"]
    if "risk_tier" in merged_df.columns:
        risk_options += sorted(merged_df["risk_tier"].dropna().astype(str).unique().tolist())

    sf1, sf2, sf3 = st.columns(3)
    with sf1:
        selected_company = st.selectbox("Company", company_options, key="savings_company")
    with sf2:
        selected_terminal = st.selectbox("Terminal", terminal_options, key="savings_terminal")
    with sf3:
        selected_risk = st.selectbox("Risk Tier", risk_options, key="savings_risk")

    filtered_df = merged_df.copy()

    if selected_company != "All" and "company" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["company"] == selected_company]

    if selected_terminal != "All" and "terminal" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["terminal"] == selected_terminal]

    if selected_risk != "All" and "risk_tier" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["risk_tier"] == selected_risk]

    unique_drivers = filtered_df["driver_id"].nunique() if "driver_id" in filtered_df.columns else 0

    if "risk_tier" in filtered_df.columns:
        elevated_df = filtered_df[filtered_df["risk_tier"].isin(["yellow", "red"])]
        elevated_unique_drivers = elevated_df["driver_id"].nunique() if not elevated_df.empty else 0
    else:
        elevated_unique_drivers = 0

    total_claim_cost = filtered_df["total_cost_numeric"].sum()
    total_lost_time_days = filtered_df["lost_time_days_numeric"].sum()

    st.subheader("Current Baseline")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Unique Drivers", int(unique_drivers))
    col2.metric("Yellow + Red Drivers", int(elevated_unique_drivers))
    col3.metric("Total Claim Cost", f"${total_claim_cost:,.0f}")
    col4.metric("Lost-Time Days", f"{total_lost_time_days:,.0f}")

    st.subheader("Prevention Savings Assumptions")

    default_pct_improved = int(st.session_state.get("assump_pct_improved", 30))
    default_claim_reduction = float(st.session_state.get("assump_claim_reduction", 2500.0))
    default_ltd_avoided = float(st.session_state.get("assump_ltd_avoided", 3.0))
    default_daily_ltd_cost = float(st.session_state.get("assump_daily_ltd_cost", 300.0))
    default_program_cost = float(st.session_state.get("assump_program_cost", 5000.0))
    default_weighted_loss_factor = float(st.session_state.get("assump_weighted_loss_factor", 0.30))
    default_mod_multiplier = float(st.session_state.get("assump_mod_multiplier", 1.25))

    pct_improved = st.slider(
        "Percent of yellow/red drivers improved",
        min_value=0,
        max_value=100,
        value=default_pct_improved,
        step=5,
    )

    avg_claim_cost_reduction = st.number_input(
        "Average claim cost reduction per improved driver ($)",
        min_value=0.0,
        value=default_claim_reduction,
        step=500.0,
    )

    avg_lost_time_days_avoided = st.number_input(
        "Average lost-time days avoided per improved driver",
        min_value=0.0,
        value=default_ltd_avoided,
        step=1.0,
    )

    daily_lost_time_cost = st.number_input(
        "Daily lost-time cost ($)",
        min_value=0.0,
        value=default_daily_ltd_cost,
        step=50.0,
    )

    program_cost = st.number_input(
        "Program cost ($)",
        min_value=0.0,
        value=default_program_cost,
        step=500.0,
    )

    st.session_state["assump_pct_improved"] = pct_improved
    st.session_state["assump_claim_reduction"] = avg_claim_cost_reduction
    st.session_state["assump_ltd_avoided"] = avg_lost_time_days_avoided
    st.session_state["assump_daily_ltd_cost"] = daily_lost_time_cost
    st.session_state["assump_program_cost"] = program_cost

    improved_driver_count = elevated_unique_drivers * (pct_improved / 100.0)
    projected_claim_savings = improved_driver_count * avg_claim_cost_reduction
    projected_lost_time_savings = improved_driver_count * avg_lost_time_days_avoided * daily_lost_time_cost
    prevention_savings = projected_claim_savings + projected_lost_time_savings

    st.subheader("Prevention Savings Output")
    out1, out2, out3, out4 = st.columns(4)
    out1.metric("Improved Drivers", f"{improved_driver_count:.1f}")
    out2.metric("Projected Claim Savings", f"${projected_claim_savings:,.0f}")
    out3.metric("Projected Lost-Time Savings", f"${projected_lost_time_savings:,.0f}")
    out4.metric("Prevention Savings", f"${prevention_savings:,.0f}")

    st.subheader("RTW Savings Contribution")

    raw_rtw_days_avoided = float(st.session_state.get("rtw_days_avoided", 0.0))
    raw_rtw_placement_cost = float(st.session_state.get("rtw_placement_cost", 0.0))
    raw_rtw_gross_savings = float(st.session_state.get("rtw_gross_savings", 0.0))
    raw_rtw_net_savings = float(st.session_state.get("rtw_net_savings", 0.0))
    rtw_matches_loaded = "rtw_matches_df" in st.session_state

    rtw_company = st.session_state.get("rtw_selected_company", "All")
    rtw_terminal = st.session_state.get("rtw_selected_terminal", "All")
    rtw_driver = st.session_state.get("rtw_selected_driver", "N/A")

    use_rtw_savings = rtw_matches_loaded and context_matches_filters(selected_company, selected_terminal)

    if use_rtw_savings:
        rtw_days_avoided = raw_rtw_days_avoided
        rtw_placement_cost = raw_rtw_placement_cost
        rtw_gross_savings = raw_rtw_gross_savings
        rtw_net_savings = raw_rtw_net_savings
    else:
        rtw_days_avoided = 0.0
        rtw_placement_cost = 0.0
        rtw_gross_savings = 0.0
        rtw_net_savings = 0.0

    rtw1, rtw2, rtw3, rtw4 = st.columns(4)
    rtw1.metric("RTW Match Loaded", "Yes" if rtw_matches_loaded else "No")
    rtw2.metric("RTW Days Avoided Used", f"{rtw_days_avoided:,.1f}")
    rtw3.metric("RTW Gross Savings Used", f"${rtw_gross_savings:,.0f}")
    rtw4.metric("RTW Net Savings Used", f"${rtw_net_savings:,.0f}")

    st.write(f"RTW Context: Company={rtw_company}, Terminal={rtw_terminal}, Driver={rtw_driver}")

    st.subheader("Weighted Loss / Premium Proxy")

    weighted_loss_factor = st.number_input(
        "Weighted loss factor",
        min_value=0.0,
        value=default_weighted_loss_factor,
        step=0.05,
        help="Proxy for how much of total claims should be treated as weighted loss."
    )

    mod_multiplier = st.number_input(
        "Premium impact multiplier",
        min_value=0.0,
        value=default_mod_multiplier,
        step=0.05,
        help="Proxy multiplier that converts weighted loss reduction into premium impact."
    )

    st.session_state["assump_weighted_loss_factor"] = weighted_loss_factor
    st.session_state["assump_mod_multiplier"] = mod_multiplier

    projected_weighted_loss = total_claim_cost * weighted_loss_factor
    projected_weighted_loss_reduction = prevention_savings * weighted_loss_factor
    projected_mod_impact_savings = projected_weighted_loss_reduction * mod_multiplier

    em1, em2, em3 = st.columns(3)
    em1.metric("Projected Weighted Loss", f"${projected_weighted_loss:,.0f}")
    em2.metric("Weighted Loss Reduction", f"${projected_weighted_loss_reduction:,.0f}")
    em3.metric("Premium Impact Proxy", f"${projected_mod_impact_savings:,.0f}")

    total_projected_savings = prevention_savings + rtw_net_savings + projected_mod_impact_savings
    net_projected_savings = total_projected_savings - program_cost

    roi_multiple = 0.0
    roi_percent = 0.0
    if program_cost > 0:
        roi_multiple = total_projected_savings / program_cost
        roi_percent = (net_projected_savings / program_cost) * 100

    st.subheader("Combined Savings Output")
    comb1, comb2, comb3, comb4 = st.columns(4)
    comb1.metric("Prevention Savings", f"${prevention_savings:,.0f}")
    comb2.metric("RTW Net Savings Used", f"${rtw_net_savings:,.0f}")
    comb3.metric("Premium Impact Proxy", f"${projected_mod_impact_savings:,.0f}")
    comb4.metric("Total Projected Savings", f"${total_projected_savings:,.0f}")

    comb5, comb6 = st.columns(2)
    comb5.metric("Net Projected Savings", f"${net_projected_savings:,.0f}")
    comb6.metric("ROI", f"{roi_multiple:.2f}x")

    st.write(f"Projected ROI %: {roi_percent:,.1f}%")

    st.subheader("Savings Summary")
    summary_df = pd.DataFrame(
        {
            "metric": [
                "company_filter",
                "terminal_filter",
                "risk_filter",
                "unique_drivers",
                "yellow_red_drivers",
                "percent_improved",
                "improved_drivers",
                "projected_claim_savings",
                "projected_lost_time_savings",
                "prevention_savings",
                "rtw_context_company",
                "rtw_context_terminal",
                "rtw_context_driver",
                "rtw_days_avoided_used",
                "rtw_gross_savings_used",
                "rtw_placement_cost_used",
                "rtw_net_savings_used",
                "weighted_loss_factor",
                "projected_weighted_loss",
                "weighted_loss_reduction",
                "premium_impact_proxy",
                "total_projected_savings",
                "program_cost",
                "net_projected_savings",
                "roi_multiple",
                "roi_percent",
            ],
            "value": [
                selected_company,
                selected_terminal,
                selected_risk,
                unique_drivers,
                elevated_unique_drivers,
                f"{pct_improved}%",
                round(improved_driver_count, 1),
                round(projected_claim_savings, 2),
                round(projected_lost_time_savings, 2),
                round(prevention_savings, 2),
                rtw_company,
                rtw_terminal,
                rtw_driver,
                round(rtw_days_avoided, 1),
                round(rtw_gross_savings, 2),
                round(rtw_placement_cost, 2),
                round(rtw_net_savings, 2),
                round(weighted_loss_factor, 2),
                round(projected_weighted_loss, 2),
                round(projected_weighted_loss_reduction, 2),
                round(projected_mod_impact_savings, 2),
                round(total_projected_savings, 2),
                round(program_cost, 2),
                round(net_projected_savings, 2),
                round(roi_multiple, 2),
                round(roi_percent, 1),
            ],
        }
    )

    st.dataframe(summary_df)

    filtered_export_df = filtered_df.drop(
        columns=["total_cost_numeric", "lost_time_days_numeric"],
        errors="ignore"
    )

    csv_data = summary_df.to_csv(index=False).encode("utf-8")
    filtered_csv = filtered_export_df.to_csv(index=False).encode("utf-8")

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            label="Download savings summary as CSV",
            data=csv_data,
            file_name="savings_summary.csv",
            mime="text/csv"
        )
    with d2:
        st.download_button(
            label="Download filtered savings data CSV",
            data=filtered_csv,
            file_name="filtered_savings_data.csv",
            mime="text/csv"
        )