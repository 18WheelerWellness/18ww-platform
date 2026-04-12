from pathlib import Path
import pandas as pd
import streamlit as st


def get_storage_dir():
    project_root = Path(__file__).resolve().parents[1]
    storage_dir = project_root / "data" / "saved_state"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def save_df_to_csv(df, filename):
    storage_dir = get_storage_dir()
    file_path = storage_dir / filename
    df.to_csv(file_path, index=False)
    return file_path


def load_df_from_csv(filename):
    storage_dir = get_storage_dir()
    file_path = storage_dir / filename
    if file_path.exists():
        return pd.read_csv(file_path)
    return None


def save_session_data():
    saved = {}

    mapping = {
        "driver_cleaned_df": "driver_cleaned_df.csv",
        "rom_cleaned_df": "rom_cleaned_df.csv",
        "rom_scored_df": "rom_scored_df.csv",
        "claims_cleaned_df": "claims_cleaned_df.csv",
        "merged_driver_rom_df": "merged_driver_rom_df.csv",
        "rtw_matches_df": "rtw_matches_df.csv",
    }

    for session_key, filename in mapping.items():
        if session_key in st.session_state:
            df = st.session_state[session_key]
            if hasattr(df, "to_csv"):
                save_df_to_csv(df, filename)
                saved[session_key] = filename

    scalar_keys = [
        "rtw_restrictions",
        "rtw_gross_savings",
        "rtw_net_savings",
        "rtw_days_avoided",
        "rtw_daily_cost",
        "rtw_placement_cost",
        "rtw_selected_company",
        "rtw_selected_terminal",
        "rtw_selected_driver",
        "rtw_selected_tier",
    ]

    scalar_path = get_storage_dir() / "scalar_state.json"
    scalar_data = {}
    for key in scalar_keys:
        if key in st.session_state:
            scalar_data[key] = st.session_state[key]

    if scalar_data:
        import json
        with open(scalar_path, "w", encoding="utf-8") as f:
            json.dump(scalar_data, f, indent=2)

    return saved


def load_session_data():
    loaded = {}

    mapping = {
        "driver_cleaned_df": "driver_cleaned_df.csv",
        "rom_cleaned_df": "rom_cleaned_df.csv",
        "rom_scored_df": "rom_scored_df.csv",
        "claims_cleaned_df": "claims_cleaned_df.csv",
        "merged_driver_rom_df": "merged_driver_rom_df.csv",
        "rtw_matches_df": "rtw_matches_df.csv",
    }

    for session_key, filename in mapping.items():
        df = load_df_from_csv(filename)
        if df is not None:
            st.session_state[session_key] = df
            loaded[session_key] = filename

    scalar_path = get_storage_dir() / "scalar_state.json"
    if scalar_path.exists():
        import json
        with open(scalar_path, "r", encoding="utf-8") as f:
            scalar_data = json.load(f)
        for key, value in scalar_data.items():
            st.session_state[key] = value

    return loaded


def clear_saved_session_data():
    storage_dir = get_storage_dir()
    for file_path in storage_dir.glob("*"):
        if file_path.is_file():
            file_path.unlink()