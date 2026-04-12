import streamlit as st
import pandas as pd
import numpy as np

from io_layer.google_company_store import load_company_rows_from_shared_tab

ROM_MMI_TAB_NAME = "rom_mmi"

BRAND_NAVY = "#0F1B38"
BRAND_SILVER = "#EEF1F8"
BRAND_SLATE = "#52606F"


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


def _fmt_money(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"${val:,.0f}"


def _fmt_pct(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"{val:.1f}%"


def _load_rom_mmi(company_name: str) -> pd.DataFrame:
    try:
        df = load_company_rows_from_shared_tab(company_name, ROM_MMI_TAB_NAME)
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    expected_cols = [
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
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""

    text_cols = [
        "company_name", "state", "driver_id", "driver_name", "claim_number",
        "body_part", "movement", "side", "status", "assessment_date", "assessor", "notes",
    ]
    for col in text_cols:
        df[col] = df[col].apply(_safe_text)

    numeric_cols = [
        "deficit_vs_baseline_pct",
        "impairment_estimate_without_baseline_pct",
        "impairment_estimate_with_baseline_pct",
        "protected_value_conservative",
        "protected_value_expected",
        "protected_value_aggressive",
    ]
    for col in numeric_cols:
        df[col] = df[col].apply(_to_float)

    return df


def _top_sum(df: pd.DataFrame, group_col: str, sum_col: str, top_n: int = 10, label: str = "Item") -> pd.DataFrame:
    work = df.copy()
    work[group_col] = work[group_col].apply(_safe_text)
    work = work[work[group_col] != ""]
    if work.empty:
        return pd.DataFrame(columns=[label, "Value"])
    out = (
        work.groupby(group_col, dropna=False)[sum_col]
        .sum(min_count=1)
        .reset_index()
        .sort_values(sum_col, ascending=False)
        .head(top_n)
    )
    out.columns = [label, "Value"]
    return out


def _driver_label(row) -> str:
    name = _safe_text(row.get("driver_name"))
    driver_id = _safe_text(row.get("driver_id"))
    if driver_id:
        return f"{name} ({driver_id})" if name else driver_id
    return name


def render_saving_rom_mmi_page():
    st.header("Saving ROM/MMI")
    st.caption("Savings view for baseline-protected value from pre-injury ROM baselines across conservative, expected, and aggressive bands.")

    company_name = st.session_state.get("company_name", "")
    df = _load_rom_mmi(company_name)

    if df.empty:
        st.info("No ROM/MMI data found yet. Save rows on Operations → ROM/MMI first.")
        return

    total_rows = len(df)
    total_conservative = df["protected_value_conservative"].dropna().sum() if not df["protected_value_conservative"].dropna().empty else 0
    total_expected = df["protected_value_expected"].dropna().sum() if not df["protected_value_expected"].dropna().empty else 0
    total_aggressive = df["protected_value_aggressive"].dropna().sum() if not df["protected_value_aggressive"].dropna().empty else 0

    avg_with_baseline = df["impairment_estimate_with_baseline_pct"].dropna().mean() if not df["impairment_estimate_with_baseline_pct"].dropna().empty else None
    avg_without_baseline = df["impairment_estimate_without_baseline_pct"].dropna().mean() if not df["impairment_estimate_without_baseline_pct"].dropna().empty else None
    avg_deficit_baseline = df["deficit_vs_baseline_pct"].dropna().mean() if not df["deficit_vs_baseline_pct"].dropna().empty else None

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ROM/MMI Rows", total_rows)
    m2.metric("Protected Value - Conservative", _fmt_money(total_conservative))
    m3.metric("Protected Value - Expected", _fmt_money(total_expected))
    m4.metric("Protected Value - Aggressive", _fmt_money(total_aggressive))

    m5, m6, m7 = st.columns(3)
    m5.metric("Avg Impairment W/O Baseline", _fmt_pct(avg_without_baseline))
    m6.metric("Avg Impairment With Baseline", _fmt_pct(avg_with_baseline))
    m7.metric("Avg Deficit vs Baseline", _fmt_pct(avg_deficit_baseline))

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Savings by State")
        state_rollup = (
            df.groupby("state", dropna=False)
            .agg(
                rows=("state", "size"),
                protected_conservative=("protected_value_conservative", "sum"),
                protected_expected=("protected_value_expected", "sum"),
                protected_aggressive=("protected_value_aggressive", "sum"),
            )
            .reset_index()
            .sort_values("protected_expected", ascending=False)
        )
        if state_rollup.empty:
            st.caption("No state data.")
        else:
            state_rollup["protected_conservative"] = state_rollup["protected_conservative"].apply(_fmt_money)
            state_rollup["protected_expected"] = state_rollup["protected_expected"].apply(_fmt_money)
            state_rollup["protected_aggressive"] = state_rollup["protected_aggressive"].apply(_fmt_money)
            state_rollup.columns = [
                "State",
                "Rows",
                "Protected $ Conservative",
                "Protected $ Expected",
                "Protected $ Aggressive",
            ]
            st.dataframe(state_rollup, use_container_width=True, hide_index=True)

    with c2:
        st.subheader("Top Savings by Body Part")
        top_body = _top_sum(df, "body_part", "protected_value_expected", top_n=10, label="Body Part")
        if top_body.empty:
            st.caption("No body part savings yet.")
        else:
            top_body["Value"] = top_body["Value"].apply(_fmt_money)
            top_body.columns = ["Body Part", "Protected $ Expected"]
            st.dataframe(top_body, use_container_width=True, hide_index=True)

    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Top Savings by Movement")
        top_move = _top_sum(df, "movement", "protected_value_expected", top_n=10, label="Movement")
        if top_move.empty:
            st.caption("No movement savings yet.")
        else:
            top_move["Value"] = top_move["Value"].apply(_fmt_money)
            top_move.columns = ["Movement", "Protected $ Expected"]
            st.dataframe(top_move, use_container_width=True, hide_index=True)

    with c4:
        st.subheader("Top Savings by Claim")
        claim_rollup = (
            df.groupby("claim_number", dropna=False)
            .agg(
                driver_name=("driver_name", lambda s: next((x for x in s if _safe_text(x)), "")),
                protected_conservative=("protected_value_conservative", "sum"),
                protected_expected=("protected_value_expected", "sum"),
                protected_aggressive=("protected_value_aggressive", "sum"),
            )
            .reset_index()
            .sort_values("protected_expected", ascending=False)
        )
        claim_rollup = claim_rollup[claim_rollup["claim_number"].astype(str).str.strip() != ""]
        if claim_rollup.empty:
            st.caption("No claim savings yet.")
        else:
            claim_rollup["protected_conservative"] = claim_rollup["protected_conservative"].apply(_fmt_money)
            claim_rollup["protected_expected"] = claim_rollup["protected_expected"].apply(_fmt_money)
            claim_rollup["protected_aggressive"] = claim_rollup["protected_aggressive"].apply(_fmt_money)
            claim_rollup.columns = [
                "Claim Number",
                "Driver",
                "Protected $ Conservative",
                "Protected $ Expected",
                "Protected $ Aggressive",
            ]
            st.dataframe(claim_rollup.head(10), use_container_width=True, hide_index=True)

    st.subheader("Highest Savings Drivers")
    driver_rollup = (
        df.groupby(["driver_name", "driver_id"], dropna=False)
        .agg(
            protected_conservative=("protected_value_conservative", "sum"),
            protected_expected=("protected_value_expected", "sum"),
            protected_aggressive=("protected_value_aggressive", "sum"),
        )
        .reset_index()
        .sort_values("protected_expected", ascending=False)
    )
    if driver_rollup.empty:
        st.caption("No driver savings yet.")
    else:
        driver_rollup["Driver"] = driver_rollup.apply(_driver_label, axis=1)
        display_driver = driver_rollup[[
            "Driver", "protected_conservative", "protected_expected", "protected_aggressive"
        ]].head(15).copy()
        display_driver.columns = [
            "Driver",
            "Protected $ Conservative",
            "Protected $ Expected",
            "Protected $ Aggressive",
        ]
        for col in ["Protected $ Conservative", "Protected $ Expected", "Protected $ Aggressive"]:
            display_driver[col] = display_driver[col].apply(_fmt_money)
        st.dataframe(display_driver, use_container_width=True, hide_index=True)

    st.subheader("Recent ROM/MMI Savings Records")
    recent = df.copy()
    recent["_dt"] = pd.to_datetime(recent["assessment_date"], errors="coerce")
    recent = recent.sort_values("_dt", ascending=False)
    recent_display = recent[[
        "assessment_date",
        "state",
        "driver_name",
        "claim_number",
        "body_part",
        "movement",
        "deficit_vs_baseline_pct",
        "protected_value_conservative",
        "protected_value_expected",
        "protected_value_aggressive",
        "status",
    ]].head(25).copy()

    recent_display["deficit_vs_baseline_pct"] = recent_display["deficit_vs_baseline_pct"].apply(_fmt_pct)
    for col in ["protected_value_conservative", "protected_value_expected", "protected_value_aggressive"]:
        recent_display[col] = recent_display[col].apply(_fmt_money)

    recent_display.columns = [
        "Assessment Date",
        "State",
        "Driver",
        "Claim Number",
        "Body Part",
        "Movement",
        "Deficit vs Baseline",
        "Protected $ Conservative",
        "Protected $ Expected",
        "Protected $ Aggressive",
        "Status",
    ]

    st.dataframe(recent_display, use_container_width=True, hide_index=True)

    st.markdown(
        f"""
        <div style="background:{BRAND_SILVER}; border:1px solid #d7ddea; border-radius:14px; padding:16px; margin-top:12px;">
            <div style="font-weight:700; color:{BRAND_NAVY}; margin-bottom:6px;">Savings Story</div>
            <div style="color:{BRAND_SLATE};">
                This page estimates how much claim value may be protected by having pre-injury ROM baselines.
                The three bands are launch-model planning estimates designed to support executive and sales conversations.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    render_saving_rom_mmi_page()
