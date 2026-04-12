import streamlit as st
import pandas as pd
from io_layer.cleaners import clean_column_names, strip_whitespace, drop_exact_duplicates
from io_layer.validators import validate_claim_file


def show_claims():
    st.header("Claims")
    st.write("Upload a claims CSV or Excel file and preview cleaned data.")

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

            st.subheader("Raw Preview")
            st.dataframe(df)

            cleaned_df = clean_column_names(df)
            cleaned_df = strip_whitespace(cleaned_df)
            cleaned_df = drop_exact_duplicates(cleaned_df)

            validate_claim_file(cleaned_df)

            st.session_state["claims_raw_df"] = df
            st.session_state["claims_cleaned_df"] = cleaned_df

            st.subheader("Cleaned Preview")
            st.dataframe(cleaned_df)

            st.success("Claims file uploaded, cleaned, validated, and saved for other pages.")

        except Exception as e:
            st.error(f"Claims file error: {e}")
    else:
        st.subheader("Status")
        if "claims_cleaned_df" in st.session_state:
            st.success("A claims file is already loaded in session.")
        else:
            st.write("No claims file processed yet.")