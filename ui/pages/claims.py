import streamlit as st
import pandas as pd

from io_layer.cleaners import clean_column_names, strip_whitespace, drop_exact_duplicates
from io_layer.google_company_store import load_company_rows_from_shared_tab

CLAIMS_TAB_NAME = "claims"


def _first_existing_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _add_lag_metrics(df):
    df = df.copy()

    claim_date_col = _first_existing_column(df, [
        "claim_date",
        "date_of_injury",
        "injury_date",
        "doi",
    ])

    reported_date_col = _first_existing_column(df, [
        "date_reported_to_wc",
        "date_reported",
        "reported_date",
        "wc_report_date",
        "date_reported_to_carrier",
    ])

    if claim_date_col:
        df["claim_date"] = df[claim_date_col]

    if reported_date_col:
        df["date_reported_to_wc"] = df[reported_date_col]

    if "claim_date" in df.columns and "date_reported_to_wc" in df.columns:
        claim_dates = pd.to_datetime(df["claim_date"], errors="coerce")
        reported_dates = pd.to_datetime(df["date_reported_to_wc"], errors="coerce")

        df["lag_days"] = (reported_dates - claim_dates).dt.days
        df.loc[pd.to_numeric(df["lag_days"], errors="coerce") < 0, "lag_days"] = pd.NA

    return df


def _prepare_claims_df(df):
    df = clean_column_names(df)
    df = strip_whitespace(df)
    df = drop_exact_duplicates(df)

    rename_map = {
        "injury_area": "body_part",
    }
    df = df.rename(columns=rename_map)

    if "driver_id" not in df.columns:
        if "driver_name" in df.columns:
            df["driver_id"] = df["driver_name"].fillna("").astype(str)
        elif "claim_number" in df.columns:
            df["driver_id"] = df["claim_number"].fillna("").astype(str)
        else:
            df["driver_id"] = ""

    df = _add_lag_metrics(df)

    expected_cols = [
        "company_name",
        "claim_number",
        "driver_name",
        "driver_id",
        "terminal",
        "claim_date",
        "date_reported_to_wc",
        "body_part",
        "injury_description",
        "claim_stage",
        "claim_status",
        "company_avg_days_out",
        "cost_per_day",
        "lag_days",
        "actual_rtw_days",
        "cost_savings_by_claim",
        "froi_received",
        "supervisor_report_received",
        "employee_statement_received",
        "osha_301_received",
        "work_ability_received",
        "wc_notified_24h",
        "job_description_sent",
        "adjuster_packet_sent",
        "adjuster_receipt_confirmed",
        "froi_file_url",
        "osha_301_file_url",
        "work_ability_form_file_url",
        "claim_folder_url",
        "documents_last_updated",
        "notes",
        "workflow_froi_completed",
        "workflow_incident_report_completed",
        "workflow_employee_statement_completed",
        "workflow_wage_statement_completed",
        "workflow_work_ability_completed",
        "workflow_job_description_completed",
        "workflow_support_docs_sent",
        "workflow_rtw_plan_created",
        "workflow_adjuster_emailed",
        "workflow_adjuster_receipt_confirmed",
        "workflow_regular_communication",
        "workflow_restrictions_monitored",
        "workflow_full_duty_release",
        "workflow_claim_closure_confirmed",
        "workflow_phase1_notes",
        "workflow_phase2_notes",
        "workflow_phase3_notes",
        "workflow_phase4_notes",
        "workflow_general_notes",
        "workflow_completion_pct",
        "workflow_last_updated",
        "claim_type",
        "restrictions_summary",
        "next_medical_visit",
        "full_duty_release_date",
        "rtw_tier",
        "temporary_job_assignment",
        "shift_hours",
        "supervisor",
        "rtw_start_date",
        "expected_review_date",
        "adjuster_notified",
        "adjuster_approved",
        "employer_approved",
        "employee_started",
        "current_status",
        "days_injury_to_rtw",
        "plan_active",
        "estimated_days_saved",
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    return df


def show_claims():
    st.header("Claims")
    st.write("Claims loaded from Google Sheets.")

    company_name = st.session_state.get("company_name", "")

    c1, c2 = st.columns([1, 1])

    with c1:
        auto_load = st.checkbox("Auto-load on page open", value=True, key="claims_auto_load")

    with c2:
        refresh = st.button("Refresh Claims", use_container_width=True)

    should_load = (
        refresh
        or "claims_cleaned_df" not in st.session_state
        or st.session_state.get("claims_last_company") != company_name
    )

    if auto_load and should_load:
        try:
            df = load_company_rows_from_shared_tab(company_name, CLAIMS_TAB_NAME)

            if df is None or df.empty:
                st.session_state["claims_raw_df"] = pd.DataFrame()
                st.session_state["claims_cleaned_df"] = pd.DataFrame()
                st.session_state["claims_last_company"] = company_name
                st.warning("No claims found in Google Sheets.")
            else:
                cleaned_df = _prepare_claims_df(df)
                st.session_state["claims_raw_df"] = df
                st.session_state["claims_cleaned_df"] = cleaned_df
                st.session_state["claims_last_company"] = company_name
                st.success("Loaded {} claims from Google Sheets.".format(len(cleaned_df)))

        except Exception as e:
            st.error("Google Sheets load error: {}".format(e))

    claims_df = st.session_state.get("claims_cleaned_df", pd.DataFrame())

    if claims_df.empty:
        st.info("No claims loaded yet.")
        return

    st.subheader("Claims Preview")
    st.dataframe(claims_df, use_container_width=True, hide_index=True)

    st.subheader("Quick Summary")
    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.metric("Claims", len(claims_df))

    with s2:
        open_claims = 0
        if "claim_status" in claims_df.columns:
            open_claims = claims_df["claim_status"].astype(str).str.contains(
                "open|active|pending", case=False, na=False
            ).sum()
        st.metric("Open / Active", int(open_claims))

    with s3:
        avg_lag = 0
        if "lag_days" in claims_df.columns:
            lag_series = pd.to_numeric(claims_df["lag_days"], errors="coerce")
            avg_lag = round(lag_series.mean(), 1) if lag_series.notna().any() else 0
        st.metric("Avg Lag Days", avg_lag)

    with s4:
        avg_rtw = 0
        if "actual_rtw_days" in claims_df.columns:
            rtw_series = pd.to_numeric(claims_df["actual_rtw_days"], errors="coerce")
            avg_rtw = round(rtw_series.mean(), 1) if rtw_series.notna().any() else 0
        st.metric("Avg RTW Days", avg_rtw)
