import streamlit as st
import pandas as pd
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from analytics.summaries import fleet_risk_summary, top_risk_drivers
from io_layer.cleaners import clean_column_names, strip_whitespace, drop_exact_duplicates
from io_layer.validators import validate_driver_file, validate_rom_file, validate_claim_file
from scoring.risk_engine import calculate_driver_risk
from io_layer.session_store import save_session_data, load_session_data, clear_saved_session_data


def load_and_clean_file_obj(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    cleaned_df = clean_column_names(df)
    cleaned_df = strip_whitespace(cleaned_df)
    cleaned_df = drop_exact_duplicates(cleaned_df)
    return df, cleaned_df


def load_and_clean_path(file_path):
    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    cleaned_df = clean_column_names(df)
    cleaned_df = strip_whitespace(cleaned_df)
    cleaned_df = drop_exact_duplicates(cleaned_df)
    return df, cleaned_df


def _extract_google_sheet_csv_url(sheet_url: str):
    sheet_url = (sheet_url or "").strip()
    if not sheet_url:
        return None

    if "docs.google.com/spreadsheets" not in sheet_url:
        return None

    parsed = urlparse(sheet_url)
    path_parts = parsed.path.split("/")
    try:
        sheet_id = path_parts[path_parts.index("d") + 1]
    except Exception:
        return None

    qs = parse_qs(parsed.query)
    gid = qs.get("gid", ["0"])[0]

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _assign_company_if_missing(df):
    company = st.session_state.get("company_name", "")
    if not company or company == "ALL":
        return df
    if "company_name" not in df.columns and "company" not in df.columns:
        df = df.copy()
        df["company_name"] = company
    return df


def _save_driver_df(raw_df, cleaned_df):
    cleaned_df = _assign_company_if_missing(cleaned_df)
    validate_driver_file(cleaned_df)
    st.session_state["driver_raw_df"] = raw_df
    st.session_state["driver_cleaned_df"] = cleaned_df


def _save_claims_df(raw_df, cleaned_df):
    cleaned_df = _assign_company_if_missing(cleaned_df)
    validate_claim_file(cleaned_df)
    st.session_state["claims_raw_df"] = raw_df
    st.session_state["claims_cleaned_df"] = cleaned_df


def _save_rom_df(raw_df, cleaned_df):
    cleaned_df = _assign_company_if_missing(cleaned_df)
    validate_rom_file(cleaned_df)
    scored_df = calculate_driver_risk(cleaned_df)
    scored_df = _assign_company_if_missing(scored_df)
    st.session_state["rom_raw_df"] = raw_df
    st.session_state["rom_cleaned_df"] = cleaned_df
    st.session_state["rom_scored_df"] = scored_df


def load_sample_data():
    project_root = Path(__file__).resolve().parents[2]
    templates_dir = project_root / "data" / "templates"

    driver_path = templates_dir / "driver_template.csv"
    rom_path = templates_dir / "rom_template.csv"
    claims_path = templates_dir / "claims_template.csv"

    if not driver_path.exists():
        raise FileNotFoundError(f"Missing file: {driver_path}")
    if not rom_path.exists():
        raise FileNotFoundError(f"Missing file: {rom_path}")
    if not claims_path.exists():
        raise FileNotFoundError(f"Missing file: {claims_path}")

    driver_raw_df, driver_cleaned_df = load_and_clean_path(driver_path)
    rom_raw_df, rom_cleaned_df = load_and_clean_path(rom_path)
    claims_raw_df, claims_cleaned_df = load_and_clean_path(claims_path)

    _save_driver_df(driver_raw_df, driver_cleaned_df)
    _save_rom_df(rom_raw_df, rom_cleaned_df)
    _save_claims_df(claims_raw_df, claims_cleaned_df)

    return {
        "drivers_rows": len(st.session_state["driver_cleaned_df"]),
        "rom_rows": len(st.session_state["rom_cleaned_df"]),
        "claims_rows": len(st.session_state["claims_cleaned_df"]),
    }


def _template_df(kind):
    company = st.session_state.get("company_name", "")
    if kind == "drivers":
        return pd.DataFrame([
            {"company_name": company, "driver_id": "D001", "driver_name": "John Driver", "terminal": "Main", "status": "Active"}
        ])
    if kind == "claims":
        return pd.DataFrame([
            {"company_name": company, "claim_number": "C1001", "driver_id": "D001", "driver_name": "John Driver", "claim_date": "2026-01-15", "claim_type": "Lost Time", "body_part": "Shoulder", "cause": "Lifting", "total_cost": 12500, "lost_time_days": 18}
        ])
    if kind == "rtw":
        return pd.DataFrame([
            {"company_name": company, "claim_number": "C1001", "driver_name": "John Driver", "froi": "No", "osha_301": "No", "work_ability_form": "No", "restrictions_status": "No", "rtw_tier": "", "rtw_job_match": "No", "rtw_start_date": "", "next_step": "Send FROI"}
        ])
    if kind == "rom":
        return pd.DataFrame([
            {"company_name": company, "driver_id": "D001", "driver_name": "John Driver", "movement": "Shoulder Abduction Right", "value": 155}
        ])
    return pd.DataFrame()


def _template_download(label, kind, filename):
    df = _template_df(kind)
    st.download_button(
        label=label,
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


def _progress_flags():
    return {
        "drivers": "driver_cleaned_df" in st.session_state,
        "claims": "claims_cleaned_df" in st.session_state,
        "rom": "rom_scored_df" in st.session_state,
    }


def _show_progress():
    flags = _progress_flags()
    complete_count = sum(flags.values())
    progress = complete_count / 3.0

    st.subheader("Getting Started Progress")
    st.progress(progress)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Drivers Uploaded", "Yes" if flags["drivers"] else "No")
    c2.metric("Claims Uploaded", "Yes" if flags["claims"] else "No")
    c3.metric("ROM Uploaded", "Yes" if flags["rom"] else "No")
    c4.metric("Executive Views", "Unlocked" if complete_count >= 2 else "Locked")


def _show_onboarding_steps():
    flags = _progress_flags()

    st.subheader("Step-by-Step Setup")

    s1, s2, s3, s4 = st.columns(4)
    s1.info("Step 1\n\nUpload Drivers")
    s2.info("Step 2\n\nUpload Claims")
    s3.info("Step 3\n\nUpload ROM or RTW")
    s4.info("Step 4\n\nReview Dashboard")

    if not flags["drivers"]:
        st.warning("Step 1: Upload your driver roster first.")
        st.caption("Most fleets begin with drivers and claims. Once those are in, the rest of the dashboard becomes much more useful.")
    elif not flags["claims"]:
        st.warning("Step 2: Upload your claims file next.")
        st.caption("Claims data unlocks RTW, savings, reporting, and premium impact pages.")
    elif not flags["rom"]:
        st.warning("Step 3: Upload ROM data or an RTW workflow file.")
        st.caption("ROM helps with risk scoring. RTW workflow data helps with accident steps, form tracking, and return-to-work visibility.")
    else:
        st.success("Step 4: Your core datasets are in. Review your dashboard and executive pages.")


def _show_onboarding():
    st.subheader("Get your company dashboard live")
    st.caption("Upload the data you already have to unlock claims, RTW, savings, and executive reporting.")

    _show_progress()
    _show_onboarding_steps()

    st.markdown("### Step 1–3: Upload the data you already have")
    u1, u2, u3 = st.columns(3)

    with u1:
        drivers_file = st.file_uploader(
            "Upload Drivers CSV/XLSX",
            type=["csv", "xlsx", "xls"],
            key="dashboard_drivers_upload",
            help="Upload your current driver roster.",
        )
        if drivers_file is not None:
            try:
                raw_df, cleaned_df = load_and_clean_file_obj(drivers_file)
                _save_driver_df(raw_df, cleaned_df)
                st.success(f"Drivers uploaded: {len(st.session_state['driver_cleaned_df'])} rows")
            except Exception as e:
                st.error(f"Driver upload error: {e}")

    with u2:
        claims_file = st.file_uploader(
            "Upload Claims CSV/XLSX",
            type=["csv", "xlsx", "xls"],
            key="dashboard_claims_upload",
            help="Upload your claims export.",
        )
        if claims_file is not None:
            try:
                raw_df, cleaned_df = load_and_clean_file_obj(claims_file)
                _save_claims_df(raw_df, cleaned_df)
                st.success(f"Claims uploaded: {len(st.session_state['claims_cleaned_df'])} rows")
            except Exception as e:
                st.error(f"Claims upload error: {e}")

    with u3:
        rom_file = st.file_uploader(
            "Upload ROM CSV/XLSX",
            type=["csv", "xlsx", "xls"],
            key="dashboard_rom_upload",
            help="Upload ROM/baseline movement data if available.",
        )
        if rom_file is not None:
            try:
                raw_df, cleaned_df = load_and_clean_file_obj(rom_file)
                _save_rom_df(raw_df, cleaned_df)
                st.success(f"ROM uploaded: {len(st.session_state['rom_cleaned_df'])} rows")
            except Exception as e:
                st.error(f"ROM upload error: {e}")

    st.markdown("### Easy Import Route: Google Sheets")
    sheet_url = st.text_input(
        "Paste a Google Sheet tab link",
        key="dashboard_google_sheet_url",
        help="Use a tab link for drivers, claims, or ROM data.",
    )
    sheet_kind = st.selectbox(
        "This sheet contains",
        ["Drivers", "Claims", "ROM"],
        key="dashboard_google_sheet_kind",
    )

    if st.button("Import Google Sheet", key="dashboard_import_google_sheet"):
        try:
            csv_url = _extract_google_sheet_csv_url(sheet_url)
            if not csv_url:
                st.error("Invalid Google Sheets link. Paste a valid Google Sheet tab URL.")
            else:
                raw_df = pd.read_csv(csv_url)
                cleaned_df = clean_column_names(raw_df)
                cleaned_df = strip_whitespace(cleaned_df)
                cleaned_df = drop_exact_duplicates(cleaned_df)

                if sheet_kind == "Drivers":
                    _save_driver_df(raw_df, cleaned_df)
                    st.success(f"Drivers imported: {len(st.session_state['driver_cleaned_df'])} rows")
                elif sheet_kind == "Claims":
                    _save_claims_df(raw_df, cleaned_df)
                    st.success(f"Claims imported: {len(st.session_state['claims_cleaned_df'])} rows")
                else:
                    _save_rom_df(raw_df, cleaned_df)
                    st.success(f"ROM imported: {len(st.session_state['rom_cleaned_df'])} rows")
        except Exception as e:
            st.error(f"Google Sheet import error: {e}")

    st.markdown("### Download Starter Templates")
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        _template_download("Driver Template", "drivers", "driver_template.csv")
    with t2:
        _template_download("Claims Template", "claims", "claims_template.csv")
    with t3:
        _template_download("RTW Template", "rtw", "rtw_template.csv")
    with t4:
        _template_download("ROM Template", "rom", "rom_template.csv")

    st.markdown("### Other Actions")
    a1, a2, a3, a4 = st.columns(4)

    with a1:
        if st.button("Load Sample Data", use_container_width=True):
            try:
                results = load_sample_data()
                st.success(
                    f"Sample data loaded. Drivers: {results['drivers_rows']}, "
                    f"ROM rows: {results['rom_rows']}, Claims rows: {results['claims_rows']}"
                )
            except Exception as e:
                st.error(f"Sample data load error: {e}")

    with a2:
        if st.button("Save Current State", use_container_width=True):
            try:
                saved = save_session_data()
                st.success(f"Saved session data: {list(saved.keys())}")
            except Exception as e:
                st.error(f"Save state error: {e}")

    with a3:
        if st.button("Load Saved State", use_container_width=True):
            try:
                loaded = load_session_data()
                if loaded:
                    st.success(f"Loaded saved state: {list(loaded.keys())}")
                else:
                    st.warning("No saved state files found.")
            except Exception as e:
                st.error(f"Load state error: {e}")

    with a4:
        if st.button("Clear Session Data", use_container_width=True):
            keys_to_clear = [
                "driver_raw_df",
                "driver_cleaned_df",
                "rom_raw_df",
                "rom_cleaned_df",
                "rom_scored_df",
                "claims_raw_df",
                "claims_cleaned_df",
                "merged_driver_rom_df",
                "rtw_restrictions",
                "rtw_matches_df",
                "rtw_gross_savings",
                "rtw_net_savings",
                "rtw_days_avoided",
                "rtw_daily_cost",
                "rtw_placement_cost",
                "rtw_selected_company",
                "rtw_selected_terminal",
                "rtw_selected_driver",
                "rtw_selected_tier",
                "corrective_summary_df",
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            clear_saved_session_data()
            st.success("Session data and saved files cleared.")


def show_dashboard():
    if "company_name" not in st.session_state:
        st.error("No company assigned. Please log in again.")
        st.stop()

    st.header("Dashboard")

    _show_onboarding()

    st.subheader("Loaded Data Status")
    drivers_loaded = "driver_cleaned_df" in st.session_state
    rom_loaded = "rom_scored_df" in st.session_state
    claims_loaded = "claims_cleaned_df" in st.session_state

    st.write(f"Logged in company: {st.session_state['company_name']}")
    st.write(f"Drivers loaded: {'Yes' if drivers_loaded else 'No'}")
    st.write(f"ROM loaded: {'Yes' if rom_loaded else 'No'}")
    st.write(f"Claims loaded: {'Yes' if claims_loaded else 'No'}")

    if rom_loaded:
        scored_df = st.session_state["rom_scored_df"]
        if "company_name" in scored_df.columns and st.session_state["company_name"] != "ALL":
            scored_df = scored_df[scored_df["company_name"].astype(str) == str(st.session_state["company_name"])].copy()
        elif "company" in scored_df.columns and st.session_state["company_name"] != "ALL":
            scored_df = scored_df[scored_df["company"].astype(str) == str(st.session_state["company_name"])].copy()

        if scored_df.empty:
            st.info("Upload ROM data to unlock company-specific risk summaries.")
            return

        summary = fleet_risk_summary(scored_df)
        top_df = top_risk_drivers(scored_df, n=10)

        st.subheader("Quick Stats")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Drivers", summary["total_drivers"])
        c2.metric("Green Tier", summary["green_count"])
        c3.metric("Yellow Tier", summary["yellow_count"])
        c4.metric("Red Tier", summary["red_count"])

        st.subheader("Top Risk Drivers")
        st.dataframe(top_df, use_container_width=True)
    else:
        st.subheader("Quick Stats")
        st.warning("Get started by uploading your first dataset to unlock dashboard insights.")
        st.caption("Upload driver, ROM, or claims data to begin.")
