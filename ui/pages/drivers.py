ximport streamlit as st
import pandas as pd

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

def _ensure_row_id(df):
    df = df.copy()
    if "_row_id" not in df.columns:
        df["_row_id"] = [f"row_{i}" for i in range(len(df))]
    return df

def _build_editor_df(df, company_name):
    df = df.copy()

    if "company_name" not in df.columns:
        df["company_name"] = company_name

    for col in DRIVER_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    df = df[["_row_id"] + DRIVER_COLUMNS]
    return df.fillna("").astype(str)

def show_drivers():
    if "company_name" not in st.session_state:
        st.error("No company assigned.")
        st.stop()

    company_name = st.session_state["company_name"]

    st.header("Drivers")
    st.caption("This is your driver roster — everything starts here.")

    # -----------------------------
    # LOAD DATA
    # -----------------------------
    # -----------------------------
    # LOAD DATA (DEMO FIRST)
    # -----------------------------
    df = st.session_state.get("driver_cleaned_df")

    if df is None or df.empty:
        df = _blank_drivers_df(company_name)

    st.session_state["driver_cleaned_df"] = df

    full_df = _ensure_row_id(st.session_state["driver_cleaned_df"])
    editor_df = _build_editor_df(full_df, company_name)

    # -----------------------------
    # TABLE (MAIN FOCUS)
    # -----------------------------
    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="drivers_editor_table",
    )

    # -----------------------------
    # SAVE BUTTON
    # -----------------------------
    if st.button("Save Driver Updates", use_container_width=True):
        st.session_state["driver_cleaned_df"] = edited
        st.success("Driver updates saved.")

    # -----------------------------
    # EXPORT (NEW ADD)
    # -----------------------------
    st.markdown("### Export Drivers")

    export_df = edited.drop(columns=["_row_id"], errors="ignore").copy()
    csv_data = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Drivers Snapshot (CSV)",
        data=csv_data,
        file_name="drivers_snapshot.csv",
        mime="text/csv",
        use_container_width=True,
    )
