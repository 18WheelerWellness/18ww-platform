import streamlit as st
import pandas as pd

def show_drivers():
    st.header("Drivers")

    # Load demo data
    df = st.session_state.get("driver_cleaned_df", pd.DataFrame())

    if df.empty:
        st.warning("No drivers found.")
        return

    # Simple metric
    st.metric("Total Drivers", len(df))

    # Editable table
    edited = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic"
    )

    # Save button
    if st.button("Save Drivers"):
        st.session_state["driver_cleaned_df"] = edited
        st.success("Drivers saved.")
