import streamlit as st
import pandas as pd

from io_layer.cleaners import clean_column_names, strip_whitespace, drop_exact_duplicates
from io_layer.validators import validate_claim_file
from io_layer.google_company_store import load_company_rows_from_shared_tab

CLAIMS_TAB_NAME = "Claims"


def _clean_claims_df(df: pd.DataFrame) -> pd.DataFrame:
    cleaned_df = clean_column_names(df)
    cleaned_df = strip_whitespace(cleaned_df)
    cleaned_df = drop_exact_duplicates(cleaned_df)
    validate_claim_file(cleaned_df)
    return cleaned_df


def show_claims():
    st.header("Claims")
    st.write("Loads claims from Google Sheets and also allows manual upload if needed.")

    company_name = st.session_state.get("company_name", "")

    top1, top2 = st.columns([1, 1])

    with top1:
        if st.button("Load Claims from Google Sheets", use_container_width=True):
            try:
                df = load_company_rows_from_shared_tab(company_name, CLAIMS_TAB_NAME)

                if df is None or df.empty:
                    st.warning(f"No claim rows found in Google Sheets tab: {CLAIMS_TAB_NAME}")
                else:
                    cleaned_df = _clean_claims_df(df)
                    st.session_state["claims_raw_df"] = df
                    st.session_state["claims_cleaned_df"] = cleaned_df
                    st.success(f"Loaded {len(cleaned_df)} claim rows from Google Sheets.")

            except Exception as e:
                st.error(f"Google Sheets load error: {e}")

    with top2:
        if st.button("Refresh Claims", use_container_width=True):
            try:
                df = load_company_rows_from_shared_tab(company_name, CLAIMS_TAB_NAME)

                if df is None or df.empty:
                    st.warning(f"No claim rows found in Google Sheets tab: {CLAIMS_TAB_NAME}")
                else:
                    cleaned_df = _clean_claims_df(df)
                    st.session_state["claims_raw_df"] = df
                    st.session_state["claims_cleaned_df"] = cleaned_df
                    st.success(f"Refreshed {len(cleaned_df)} claim rows from Google Sheets.")

            except Exception as e:
                st.error(f"Google Sheets refresh error: {e}")

    st.markdown("---")
    st.subheader("Manual Upload Fallback")

    uploaded_file = st.file_uploader(
        "Choose a Claims CSV or Excel file",
        type=["csv", "xlsx"],
        key="claims_file"
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            cleaned_df = _clean_claims_df(df)

            st.session_state["claims_raw_df"] = df
            st.session_state["claims_cleaned_df"] = cleaned_df

            st.success("Claims file uploaded, cleaned, validated, and saved for other pages.")

        except Exception as e:
            st.error(f"Claims file error: {e}")

    st.markdown("---")
    st.subheader("Claims Preview")

    if "claims_cleaned_df" in st.session_state and not st.session_state["claims_cleaned_df"].empty:
        st.dataframe(st.session_state["claims_cleaned_df"], use_container_width=True)
    else:
        st.info("No claims loaded yet. Use Google Sheets load or manual upload.")
