import streamlit as st
import pandas as pd
from urllib.parse import urlparse, parse_qs

from io_layer.cleaners import clean_column_names, strip_whitespace, drop_exact_duplicates
from io_layer.google_company_store import (
    save_company_rows_to_shared_tab,
    load_company_rows_from_shared_tab,
)

BLANK_DRIVERS_GOOGLE_SHEET_URL = ""

DRIVER_COLUMNS = [
    "company_name",
    "driver_id",
    "driver_name",
    "terminal",
    "status",
    "job_title",
    "hire_date",
    "phone",
    "email",
    "notes",
]

def _action_message():
    st.warning("Get started by uploading your driver roster.")
    st.caption("Upload a CSV/XLSX file, import a Google Sheet tab, load from the shared drivers tab, or start with a blank driver table.")

def _extract_google_sheet_csv_url(sheet_url: str):
    sheet_url = (sheet_url or "").strip()
    if not sheet_url or "docs.google.com/spreadsheets" not in sheet_url:
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
    df = df.copy()
    if "company_name" not in df.columns and "company" not in df.columns:
        df["company_name"] = company
    elif "company" in df.columns and "company_name" not in df.columns:
        df["company_name"] = df["company"]
    return df

def _load_uploaded_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    df = clean_column_names(df)
    df = strip_whitespace(df)
    df = drop_exact_duplicates(df)
    df = _assign_company_if_missing(df)
    return df

def _blank_drivers_df(company_name):
    return pd.DataFrame([{
        "company_name": company_name,
        "driver_id": "",
        "driver_name": "",
        "terminal": "",
        "status": "Active",
        "job_title": "Driver",
        "hire_date": "",
        "phone": "",
        "email": "",
        "notes": "",
    }])

def _drivers_template(company_name):
    return pd.DataFrame([{
        "company_name": company_name,
        "driver_id": "D001",
        "driver_name": "John Driver",
        "terminal": "Main",
        "status": "Active",
        "job_title": "CDL Driver",
        "hire_date": "2026-01-15",
        "phone": "555-555-5555",
        "email": "john@example.com",
        "notes": "",
    }])

def _ensure_row_id(df):
    df = df.copy()
    if "_row_id" not in df.columns:
        df["_row_id"] = [f"row_{i}" for i in range(len(df))]
    df["_row_id"] = df["_row_id"].astype(str)
    return df

def _filter_to_company(df):
    company = st.session_state.get("company_name", "")
    if company == "ALL":
        return df.copy()
    if "company_name" in df.columns:
        return df[df["company_name"].astype(str) == str(company)].copy()
    if "company" in df.columns:
        return df[df["company"].astype(str) == str(company)].copy()
    return pd.DataFrame()

def _coerce_driver_editor_types(df):
    df = df.copy()
    text_cols = [
        "_row_id", "company_name", "driver_id", "driver_name", "terminal",
        "status", "job_title", "hire_date", "phone", "email", "notes",
    ]
    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    return df

def _build_editor_df(full_df, company_name):
    df = full_df.copy()
    if "company_name" not in df.columns:
        df["company_name"] = company_name

    for col in DRIVER_COLUMNS:
        if col not in df.columns:
            df[col] = "Active" if col == "status" else ""

    df = df[["_row_id"] + DRIVER_COLUMNS].copy()
    return _coerce_driver_editor_types(df)

def _merge_editor_back(original_full_df, edited_driver_df, company_name):
    original_full_df = _ensure_row_id(original_full_df)
    edited = edited_driver_df.copy()

    if "_row_id" not in edited.columns:
        edited["_row_id"] = [f"new_{i}" for i in range(len(edited))]
    edited["_row_id"] = edited["_row_id"].astype(str)

    for col in DRIVER_COLUMNS:
        if col not in edited.columns:
            edited[col] = ""

    edited = _coerce_driver_editor_types(edited)
    edited["company_name"] = company_name if company_name != "ALL" else edited["company_name"]

    extra_cols = [c for c in original_full_df.columns if c not in edited.columns]
    base = edited.copy()
    if extra_cols:
        extra_map = original_full_df[["_row_id"] + extra_cols].copy()
        base = base.merge(extra_map, on="_row_id", how="left")

    preferred = ["_row_id"] + DRIVER_COLUMNS
    ordered = preferred + [c for c in base.columns if c not in preferred]
    return base[ordered].copy()

def show_drivers():
    if "company_name" not in st.session_state:
        st.error("No company assigned. Please log in again.")
        st.stop()

    company_name = st.session_state["company_name"]
    st.header("Drivers")
    st.caption("Use this page to upload, import, and maintain your company driver roster.")

    if "driver_cleaned_df" not in st.session_state:
        st.session_state["driver_cleaned_df"] = _blank_drivers_df(company_name)

    full_df = _ensure_row_id(st.session_state["driver_cleaned_df"])

    st.subheader("Upload / Import Driver Data")
    st.info(
        "Need a starting point? Use the blank Drivers Google Sheet template, make your own copy, fill it out, then paste that tab link below to import it."
    )

    if BLANK_DRIVERS_GOOGLE_SHEET_URL.strip():
        st.link_button(
            "Open Blank Drivers Google Sheet Template",
            BLANK_DRIVERS_GOOGLE_SHEET_URL,
            use_container_width=True,
        )
    else:
        st.caption("Add your blank Google Sheet tab link to BLANK_DRIVERS_GOOGLE_SHEET_URL in drivers.py to show the template button here.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        uploaded = st.file_uploader("Upload Drivers CSV/XLSX", type=["csv", "xlsx", "xls"], key="drivers_upload_file")
        if uploaded is not None:
            try:
                imported_df = _load_uploaded_file(uploaded)
                imported_df = _ensure_row_id(imported_df)
                st.session_state["driver_cleaned_df"] = imported_df
                st.success(f"Drivers uploaded: {len(imported_df)} rows")
                st.rerun()
            except Exception as e:
                st.error(f"Driver upload error: {e}")

    with c2:
        sheet_url = st.text_input("Google Sheet tab link", key="drivers_google_sheet_url", help="Paste a Google Sheet tab link for driver intake.")
        if st.button("Import Google Sheet", key="drivers_import_google_sheet"):
            try:
                csv_url = _extract_google_sheet_csv_url(sheet_url)
                if not csv_url:
                    st.error("Invalid Google Sheets link.")
                else:
                    imported_df = pd.read_csv(csv_url)
                    imported_df = clean_column_names(imported_df)
                    imported_df = strip_whitespace(imported_df)
                    imported_df = drop_exact_duplicates(imported_df)
                    imported_df = _assign_company_if_missing(imported_df)
                    imported_df = _ensure_row_id(imported_df)
                    st.session_state["driver_cleaned_df"] = imported_df
                    st.success(f"Drivers imported: {len(imported_df)} rows")
                    st.rerun()
            except Exception as e:
                st.error(f"Google Sheet import error: {e}")

    with c3:
        if st.button("Load Company Drivers from Google", use_container_width=True):
            try:
                imported_df = load_company_rows_from_shared_tab(company_name, "drivers")
                if imported_df.empty:
                    st.warning(f"No driver rows found in shared 'drivers' tab for {company_name}")
                else:
                    imported_df = clean_column_names(imported_df)
                    imported_df = strip_whitespace(imported_df)
                    imported_df = drop_exact_duplicates(imported_df)
                    imported_df = _assign_company_if_missing(imported_df)
                    imported_df = _ensure_row_id(imported_df)
                    st.session_state["driver_cleaned_df"] = imported_df
                    st.success(f"Loaded {len(imported_df)} driver rows from shared Google drivers tab")
                    st.rerun()
            except Exception as e:
                st.error(f"Google shared tab load error: {e}")

    with c4:
        template_df = _drivers_template(company_name)
        st.download_button(
            "Download Drivers CSV Template",
            data=template_df.to_csv(index=False).encode("utf-8"),
            file_name="drivers_template.csv",
            mime="text/csv",
            use_container_width=True,
        )

    company_df = _filter_to_company(full_df)
    if company_df.empty and company_name != "ALL":
        _action_message()
        if st.button("Start Blank Drivers Table", key="start_blank_drivers"):
            st.session_state["driver_cleaned_df"] = _blank_drivers_df(company_name)
            st.rerun()
        return

    editor_df = _build_editor_df(company_df if not company_df.empty else _blank_drivers_df(company_name), company_name)

    st.subheader("Driver Roster Table")
    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "_row_id": st.column_config.TextColumn("_row_id", disabled=True, width="small"),
            "company_name": st.column_config.TextColumn("Company", disabled=(company_name != "ALL")),
            "driver_id": st.column_config.TextColumn("Driver ID"),
            "driver_name": st.column_config.TextColumn("Driver Name"),
            "terminal": st.column_config.TextColumn("Terminal"),
            "status": st.column_config.SelectboxColumn("Status", options=["Active", "Inactive", "Leave", "Terminated"]),
            "job_title": st.column_config.TextColumn("Job Title"),
            "hire_date": st.column_config.TextColumn("Hire Date"),
            "phone": st.column_config.TextColumn("Phone"),
            "email": st.column_config.TextColumn("Email"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
        key="drivers_editor_table",
    )

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("Save Driver Updates", use_container_width=True):
            updated_full = _merge_editor_back(full_df, edited, company_name)
            st.session_state["driver_cleaned_df"] = updated_full
            st.success("Driver updates saved for this session.")

    with b2:
        if st.button("Save Drivers to Google", use_container_width=True):
            try:
                export_df = edited.drop(columns=["_row_id"], errors="ignore").copy()
                saved_count = save_company_rows_to_shared_tab(export_df, company_name, "drivers")
                updated_full = _merge_editor_back(full_df, edited, company_name)
                st.session_state["driver_cleaned_df"] = updated_full
                st.success(f"Saved {saved_count} driver rows to shared Google 'drivers' tab")
            except Exception as e:
                st.error(f"Google save error: {e}")

    with b3:
        if st.button("Reset to Blank Drivers Table", use_container_width=True):
            st.session_state["driver_cleaned_df"] = _blank_drivers_df(company_name)
            st.rerun()

    with b4:
        csv_data = edited.drop(columns=["_row_id"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download Drivers CSV",
            data=csv_data,
            file_name="drivers_roster.csv",
            mime="text/csv",
            use_container_width=True,
        )
