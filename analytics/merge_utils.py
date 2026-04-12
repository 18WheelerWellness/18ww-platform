import pandas as pd
import streamlit as st


def build_merged_driver_rom_claims():
    drivers_loaded = "driver_cleaned_df" in st.session_state
    rom_loaded = "rom_scored_df" in st.session_state
    claims_loaded = "claims_cleaned_df" in st.session_state

    if not (drivers_loaded and rom_loaded):
        return None

    driver_df = st.session_state["driver_cleaned_df"].copy()
    scored_df = st.session_state["rom_scored_df"].copy()

    if "driver_id" in driver_df.columns:
        driver_df["driver_id"] = driver_df["driver_id"].astype(str)

    if "driver_id" in scored_df.columns:
        scored_df["driver_id"] = scored_df["driver_id"].astype(str)

    merged_df = pd.merge(driver_df, scored_df, on="driver_id", how="left")

    if claims_loaded:
        claims_df = st.session_state["claims_cleaned_df"].copy()

        if "driver_id" in claims_df.columns:
            claims_df["driver_id"] = claims_df["driver_id"].astype(str)

        merged_df = pd.merge(merged_df, claims_df, on="driver_id", how="left")

    st.session_state["merged_driver_rom_df"] = merged_df
    return merged_df


def get_merged_driver_rom_claims():
    if "merged_driver_rom_df" in st.session_state:
        return st.session_state["merged_driver_rom_df"]

    return build_merged_driver_rom_claims()