
import streamlit as st
import pandas as pd
import numpy as np

from io_layer.google_company_store import (
    load_company_rows_from_shared_tab,
    save_company_rows_to_shared_tab,
)

ROM_MMI_TAB_NAME = "rom_mmi"

TIER1_MOVEMENTS = {
    "Cervical": [
        ("Flexion", 50),
        ("Extension", 60),
        ("Lateral Flexion", 45),
        ("Rotation", 80),
    ],
    "Thoracolumbar": [
        ("Flexion", 60),
        ("Extension", 25),
        ("Side Bend", 25),
        ("Rotation", 30),
    ],
    "Shoulder": [
        ("Flexion", 180),
        ("Abduction", 180),
        ("Internal Rotation", 70),
        ("External Rotation", 90),
    ],
    "Hip": [
        ("Flexion", 120),
    ],
    "Knee": [
        ("Flexion", 135),
        ("Extension", 0),
    ],
    "Ankle": [
        ("Dorsiflexion", 20),
        ("Plantarflexion", 50),
    ],
    "Wrist": [
        ("Flexion", 80),
        ("Extension", 70),
    ],
}

STATE_OPTIONS = ["Michigan", "Illinois", "Texas"]
BODY_PART_OPTIONS = [""] + list(TIER1_MOVEMENTS.keys())
SIDE_OPTIONS = ["", "Left", "Right", "Bilateral", "N/A"]
STATUS_OPTIONS = ["", "Baseline", "Post-Injury", "MMI Review", "Closed"]

# Launch-model state tuning.
# These are planning estimates, not legal determinations.
STATE_VALUE_PER_POINT = {
    "Michigan": {"conservative": 1500, "expected": 3000, "aggressive": 5000},
    "Illinois": {"conservative": 1750, "expected": 3500, "aggressive": 6000},
    "Texas": {"conservative": 1250, "expected": 2500, "aggressive": 4500},
}

STATE_IMPAIRMENT_MULTIPLIER = {
    "Michigan": 0.22,
    "Illinois": 0.25,
    "Texas": 0.20,
}

ROM_MMI_COLUMNS = [
    "company_name",
    "state",
    "driver_id",
    "driver_name",
    "claim_number",
    "body_part",
    "movement",
    "side",
    "standard_rom_deg",
    "baseline_rom_deg",
    "post_injury_rom_deg",
    "deficit_vs_standard_deg",
    "deficit_vs_standard_pct",
    "deficit_vs_baseline_deg",
    "deficit_vs_baseline_pct",
    "impairment_estimate_without_baseline_pct",
    "impairment_estimate_with_baseline_pct",
    "value_without_baseline_conservative",
    "value_with_baseline_conservative",
    "protected_value_conservative",
    "value_without_baseline_expected",
    "value_with_baseline_expected",
    "protected_value_expected",
    "value_without_baseline_aggressive",
    "value_with_baseline_aggressive",
    "protected_value_aggressive",
    "status",
    "assessment_date",
    "assessor",
    "notes",
]


def _safe_text(val) -> str:
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def _to_float(val):
    try:
        text = _safe_text(val).replace("%", "").replace("$", "").replace(",", "")
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def _fmt_num(val, suffix=""):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    if float(val).is_integer():
        return f"{int(val)}{suffix}"
    return f"{val:.1f}{suffix}"


def _movement_options(body_part: str):
    return [m for m, _ in TIER1_MOVEMENTS.get(body_part, [])]


def _standard_rom_lookup(body_part: str, movement: str):
    for m, v in TIER1_MOVEMENTS.get(body_part, []):
        if m == movement:
            return float(v)
    return None


def _estimate_impairment(deficit_pct: float | None, state: str):
    if deficit_pct is None:
        return None
    mult = STATE_IMPAIRMENT_MULTIPLIER.get(state, STATE_IMPAIRMENT_MULTIPLIER["Michigan"])
    return round(deficit_pct * mult, 1)


def _estimate_value(impairment_pct: float | None, state: str, mode: str):
    if impairment_pct is None:
        return None
    per_point = STATE_VALUE_PER_POINT.get(state, STATE_VALUE_PER_POINT["Michigan"]).get(mode, 0)
    return round(impairment_pct * per_point, 0)


def _compute_row_metrics(row):
    state = _safe_text(row.get("state")) or "Michigan"
    standard = _to_float(row.get("standard_rom_deg"))
    baseline = _to_float(row.get("baseline_rom_deg"))
    post = _to_float(row.get("post_injury_rom_deg"))

    if standard is None:
        standard = _standard_rom_lookup(_safe_text(row.get("body_part")), _safe_text(row.get("movement")))

    deficit_standard_deg = None
    deficit_standard_pct = None
    deficit_baseline_deg = None
    deficit_baseline_pct = None
    impairment_without = None
    impairment_with = None

    if standard is not None and post is not None:
        if standard == 0:
            deficit_standard_deg = 0.0
            deficit_standard_pct = 0.0
        else:
            deficit_standard_deg = max(standard - post, 0)
            deficit_standard_pct = round((deficit_standard_deg / standard) * 100.0, 1)
        impairment_without = _estimate_impairment(deficit_standard_pct, state)

    if baseline is not None and post is not None:
        if baseline == 0:
            deficit_baseline_deg = 0.0
            deficit_baseline_pct = 0.0
        else:
            deficit_baseline_deg = max(baseline - post, 0)
            deficit_baseline_pct = round((deficit_baseline_deg / baseline) * 100.0, 1)
        impairment_with = _estimate_impairment(deficit_baseline_pct, state)

    value_without_conservative = _estimate_value(impairment_without, state, "conservative")
    value_with_conservative = _estimate_value(impairment_with, state, "conservative")
    protected_conservative = None if value_without_conservative is None or value_with_conservative is None else max(value_without_conservative - value_with_conservative, 0)

    value_without_expected = _estimate_value(impairment_without, state, "expected")
    value_with_expected = _estimate_value(impairment_with, state, "expected")
    protected_expected = None if value_without_expected is None or value_with_expected is None else max(value_without_expected - value_with_expected, 0)

    value_without_aggressive = _estimate_value(impairment_without, state, "aggressive")
    value_with_aggressive = _estimate_value(impairment_with, state, "aggressive")
    protected_aggressive = None if value_without_aggressive is None or value_with_aggressive is None else max(value_without_aggressive - value_with_aggressive, 0)

    return {
        "standard_rom_deg": standard,
        "deficit_vs_standard_deg": deficit_standard_deg,
        "deficit_vs_standard_pct": deficit_standard_pct,
        "deficit_vs_baseline_deg": deficit_baseline_deg,
        "deficit_vs_baseline_pct": deficit_baseline_pct,
        "impairment_estimate_without_baseline_pct": impairment_without,
        "impairment_estimate_with_baseline_pct": impairment_with,
        "value_without_baseline_conservative": value_without_conservative,
        "value_with_baseline_conservative": value_with_conservative,
        "protected_value_conservative": protected_conservative,
        "value_without_baseline_expected": value_without_expected,
        "value_with_baseline_expected": value_with_expected,
        "protected_value_expected": protected_expected,
        "value_without_baseline_aggressive": value_without_aggressive,
        "value_with_baseline_aggressive": value_with_aggressive,
        "protected_value_aggressive": protected_aggressive,
    }


def _normalize_rom_df(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    if df.empty:
        df = pd.DataFrame(columns=ROM_MMI_COLUMNS)

    df = df.copy()
    for col in ROM_MMI_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    if company_name and company_name != "ALL":
        df["company_name"] = company_name

    if "state" not in df.columns:
        df["state"] = "Michigan"

    text_cols = [
        "company_name", "state", "driver_id", "driver_name", "claim_number",
        "body_part", "movement", "side", "status", "assessment_date",
        "assessor", "notes",
    ]
    for col in text_cols:
        df[col] = df[col].apply(_safe_text).astype(str)

    numeric_cols = [
        "standard_rom_deg", "baseline_rom_deg", "post_injury_rom_deg",
        "deficit_vs_standard_deg", "deficit_vs_standard_pct",
        "deficit_vs_baseline_deg", "deficit_vs_baseline_pct",
        "impairment_estimate_without_baseline_pct",
        "impairment_estimate_with_baseline_pct",
        "value_without_baseline_conservative",
        "value_with_baseline_conservative",
        "protected_value_conservative",
        "value_without_baseline_expected",
        "value_with_baseline_expected",
        "protected_value_expected",
        "value_without_baseline_aggressive",
        "value_with_baseline_aggressive",
        "protected_value_aggressive",
    ]
    for col in numeric_cols:
        df[col] = df[col].apply(_to_float)

    metrics_rows = []
    for _, row in df.iterrows():
        calc = _compute_row_metrics(row)
        merged = row.to_dict()
        merged.update(calc)
        metrics_rows.append(merged)

    out = pd.DataFrame(metrics_rows)
    return out[ROM_MMI_COLUMNS].copy()


def _load_driver_options(company_name: str) -> pd.DataFrame:
    df = st.session_state.get("driver_cleaned_df")
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["driver_name", "driver_id", "company_name"])

    work = df.copy()
    if "company_name" in work.columns and company_name and company_name != "ALL":
        work = work[work["company_name"].astype(str).str.strip() == str(company_name).strip()].copy()

    for col in ["driver_name", "driver_id", "company_name"]:
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].apply(_safe_text)

    work = work[work["driver_name"] != ""].drop_duplicates(subset=["driver_name", "driver_id"])
    return work.reset_index(drop=True)


def render_rom_mmi_page():
    st.header("ROM / MMI")
    st.caption("Use Tier 1 movement rows, state selection, and conservative/expected/aggressive value bands to estimate baseline-protected value.")

    company_name = st.session_state.get("company_name", "")
    is_all_view = str(company_name).strip().upper() == "ALL"
    if is_all_view:
        st.warning("Admin ALL view is read-only. Select a specific company in the sidebar to edit ROM/MMI rows.")

    driver_options_df = _load_driver_options(company_name)

    with st.expander("Quick add Tier 1 ROM/MMI row", expanded=False):
        default_driver_name = ""
        default_driver_id = ""

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            quick_state = st.selectbox("State", STATE_OPTIONS, key="rom_quick_state")
        with c2:
            if not driver_options_df.empty:
                labels = [""] + [
                    f"{r['driver_name']} | {r['driver_id']}" if r["driver_id"] else r["driver_name"]
                    for _, r in driver_options_df.iterrows()
                ]
                selected_driver_label = st.selectbox("Driver", labels, key="rom_quick_driver")
                if selected_driver_label:
                    idx = labels.index(selected_driver_label) - 1
                    selected_driver = driver_options_df.iloc[idx]
                    default_driver_name = _safe_text(selected_driver.get("driver_name"))
                    default_driver_id = _safe_text(selected_driver.get("driver_id"))
            else:
                st.caption("Load driver roster first to use driver picklist.")
        with c3:
            quick_claim = st.text_input("Claim Number", key="rom_quick_claim")
        with c4:
            quick_body_part = st.selectbox("Body Part", BODY_PART_OPTIONS, key="rom_quick_body_part")

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            movement_options = [""] + _movement_options(quick_body_part)
            quick_movement = st.selectbox("Movement", movement_options, key="rom_quick_movement")
        with c6:
            quick_side = st.selectbox("Side", SIDE_OPTIONS, key="rom_quick_side")
        with c7:
            quick_standard = _standard_rom_lookup(quick_body_part, quick_movement)
            st.text_input("Standard ROM (deg)", value=_fmt_num(quick_standard), disabled=True, key="rom_quick_standard_display")
        with c8:
            quick_baseline = st.text_input("Baseline ROM (deg)", key="rom_quick_baseline")

        c9, c10, c11, c12 = st.columns(4)
        with c9:
            quick_post = st.text_input("Post-Injury ROM (deg)", key="rom_quick_post")
        with c10:
            quick_status = st.selectbox("Status", STATUS_OPTIONS, index=1, key="rom_quick_status")
        with c11:
            quick_date = st.text_input("Assessment Date", value=pd.Timestamp.now().strftime("%Y-%m-%d"), key="rom_quick_date")
        with c12:
            quick_assessor = st.text_input("Assessor", value="18WW", key="rom_quick_assessor")

        quick_notes = st.text_input("Notes", key="rom_quick_notes")

        preview_row = {
            "state": quick_state,
            "body_part": quick_body_part,
            "movement": quick_movement,
            "standard_rom_deg": quick_standard,
            "baseline_rom_deg": _to_float(quick_baseline),
            "post_injury_rom_deg": _to_float(quick_post),
        }
        preview_calc = _compute_row_metrics(preview_row)

        p1, p2, p3 = st.columns(3)
        p1.metric("Protected Value - Conservative", "-" if preview_calc["protected_value_conservative"] is None else f"${preview_calc['protected_value_conservative']:,.0f}")
        p2.metric("Protected Value - Expected", "-" if preview_calc["protected_value_expected"] is None else f"${preview_calc['protected_value_expected']:,.0f}")
        p3.metric("Protected Value - Aggressive", "-" if preview_calc["protected_value_aggressive"] is None else f"${preview_calc['protected_value_aggressive']:,.0f}")

        if st.button("Add ROM/MMI Row", use_container_width=True, disabled=is_all_view):
            current = load_company_rows_from_shared_tab(company_name, ROM_MMI_TAB_NAME)
            current = _normalize_rom_df(current, company_name)

            new_row = pd.DataFrame([{
                "company_name": company_name,
                "state": quick_state,
                "driver_id": default_driver_id,
                "driver_name": default_driver_name,
                "claim_number": quick_claim,
                "body_part": quick_body_part,
                "movement": quick_movement,
                "side": quick_side,
                "standard_rom_deg": quick_standard,
                "baseline_rom_deg": _to_float(quick_baseline),
                "post_injury_rom_deg": _to_float(quick_post),
                "deficit_vs_standard_deg": None,
                "deficit_vs_standard_pct": None,
                "deficit_vs_baseline_deg": None,
                "deficit_vs_baseline_pct": None,
                "impairment_estimate_without_baseline_pct": None,
                "impairment_estimate_with_baseline_pct": None,
                "value_without_baseline_conservative": None,
                "value_with_baseline_conservative": None,
                "protected_value_conservative": None,
                "value_without_baseline_expected": None,
                "value_with_baseline_expected": None,
                "protected_value_expected": None,
                "value_without_baseline_aggressive": None,
                "value_with_baseline_aggressive": None,
                "protected_value_aggressive": None,
                "status": quick_status,
                "assessment_date": quick_date,
                "assessor": quick_assessor,
                "notes": quick_notes,
            }])

            updated = pd.concat([current, new_row], ignore_index=True)
            updated = _normalize_rom_df(updated, company_name)
            save_company_rows_to_shared_tab(updated, company_name, ROM_MMI_TAB_NAME)
            st.success("ROM/MMI row added.")
            st.rerun()

    rom_df = load_company_rows_from_shared_tab(company_name, ROM_MMI_TAB_NAME)
    rom_df = _normalize_rom_df(rom_df, company_name)
    st.session_state["rom_mmi_df"] = rom_df.copy()

    total_rows = len(rom_df)
    avg_standard_deficit = rom_df["deficit_vs_standard_pct"].dropna().mean() if not rom_df.empty else None
    avg_baseline_deficit = rom_df["deficit_vs_baseline_pct"].dropna().mean() if not rom_df.empty else None
    total_protected_expected = rom_df["protected_value_expected"].dropna().sum() if not rom_df.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ROM/MMI Rows", total_rows)
    m2.metric("Avg Deficit vs Standard", "-" if avg_standard_deficit is None or pd.isna(avg_standard_deficit) else f"{avg_standard_deficit:.1f}%")
    m3.metric("Avg Deficit vs Baseline", "-" if avg_baseline_deficit is None or pd.isna(avg_baseline_deficit) else f"{avg_baseline_deficit:.1f}%")
    m4.metric("Protected Value - Expected", f"${total_protected_expected:,.0f}")

    st.info("This page uses launch-model planning estimates by state. It is built for executive planning and sales proof, not legal impairment determination.")

    display_df = rom_df.copy()
    pct_cols = [
        "deficit_vs_standard_pct",
        "deficit_vs_baseline_pct",
        "impairment_estimate_without_baseline_pct",
        "impairment_estimate_with_baseline_pct",
    ]
    for col in pct_cols:
        display_df[col] = display_df[col].apply(lambda x: _fmt_num(x, "%"))
    for col in [
        "standard_rom_deg", "baseline_rom_deg", "post_injury_rom_deg",
        "deficit_vs_standard_deg", "deficit_vs_baseline_deg",
    ]:
        display_df[col] = display_df[col].apply(_fmt_num)
    for col in [
        "value_without_baseline_conservative", "value_with_baseline_conservative", "protected_value_conservative",
        "value_without_baseline_expected", "value_with_baseline_expected", "protected_value_expected",
        "value_without_baseline_aggressive", "value_with_baseline_aggressive", "protected_value_aggressive",
    ]:
        display_df[col] = display_df[col].apply(lambda x: _fmt_num(x))

    st.subheader("ROM / MMI Table")
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        disabled=is_all_view,
        key="rom_mmi_editor",
        column_config={
            "company_name": st.column_config.TextColumn("Company", disabled=True),
            "state": st.column_config.SelectboxColumn("State", options=STATE_OPTIONS),
            "driver_id": st.column_config.TextColumn("Driver ID"),
            "driver_name": st.column_config.TextColumn("Driver Name"),
            "claim_number": st.column_config.TextColumn("Claim Number"),
            "body_part": st.column_config.SelectboxColumn("Body Part", options=BODY_PART_OPTIONS),
            "movement": st.column_config.TextColumn("Movement"),
            "side": st.column_config.SelectboxColumn("Side", options=SIDE_OPTIONS),
            "standard_rom_deg": st.column_config.TextColumn("Standard ROM"),
            "baseline_rom_deg": st.column_config.TextColumn("Baseline ROM"),
            "post_injury_rom_deg": st.column_config.TextColumn("Post-Injury ROM"),
            "deficit_vs_standard_deg": st.column_config.TextColumn("Deficit vs Standard", disabled=True),
            "deficit_vs_standard_pct": st.column_config.TextColumn("Deficit vs Standard %", disabled=True),
            "deficit_vs_baseline_deg": st.column_config.TextColumn("Deficit vs Baseline", disabled=True),
            "deficit_vs_baseline_pct": st.column_config.TextColumn("Deficit vs Baseline %", disabled=True),
            "impairment_estimate_without_baseline_pct": st.column_config.TextColumn("Impairment % W/O Baseline", disabled=True),
            "impairment_estimate_with_baseline_pct": st.column_config.TextColumn("Impairment % With Baseline", disabled=True),
            "value_without_baseline_conservative": st.column_config.TextColumn("W/O Baseline $ Conservative", disabled=True),
            "value_with_baseline_conservative": st.column_config.TextColumn("With Baseline $ Conservative", disabled=True),
            "protected_value_conservative": st.column_config.TextColumn("Protected $ Conservative", disabled=True),
            "value_without_baseline_expected": st.column_config.TextColumn("W/O Baseline $ Expected", disabled=True),
            "value_with_baseline_expected": st.column_config.TextColumn("With Baseline $ Expected", disabled=True),
            "protected_value_expected": st.column_config.TextColumn("Protected $ Expected", disabled=True),
            "value_without_baseline_aggressive": st.column_config.TextColumn("W/O Baseline $ Aggressive", disabled=True),
            "value_with_baseline_aggressive": st.column_config.TextColumn("With Baseline $ Aggressive", disabled=True),
            "protected_value_aggressive": st.column_config.TextColumn("Protected $ Aggressive", disabled=True),
            "status": st.column_config.SelectboxColumn("Status", options=STATUS_OPTIONS),
            "assessment_date": st.column_config.TextColumn("Assessment Date"),
            "assessor": st.column_config.TextColumn("Assessor"),
            "notes": st.column_config.TextColumn("Notes", width="large"),
        },
    )

    if st.button("Save ROM/MMI", use_container_width=True, disabled=is_all_view):
        save_df = _normalize_rom_df(edited_df, company_name)
        save_company_rows_to_shared_tab(save_df, company_name, ROM_MMI_TAB_NAME)
        st.session_state["rom_mmi_df"] = save_df.copy()
        st.success("ROM/MMI saved.")
        st.rerun()


def show_rom_mmi():
    render_rom_mmi_page()


if __name__ == "__main__":
    render_rom_mmi_page()
