import io
import pandas as pd
import streamlit as st
from io_layer.google_company_store import load_company_rows_from_shared_tab, save_company_rows_to_shared_tab

WORKFLOW_TAB = "rtw_plan"
CLAIMS_TAB = "claims"

RTW_PLAN_CORE_FIELDS = [
    "company_name","claim_number","driver_name","injury_area","injury_description","date_of_injury",
    "claim_stage","work_ability_received","restrictions_summary","next_medical_visit",
    "full_duty_release_date","rtw_tier","temporary_job_assignment","shift_hours","supervisor",
    "rtw_start_date","expected_review_date","adjuster_notified","adjuster_approved",
    "employer_approved","employee_started","current_status","days_injury_to_rtw","plan_active","notes",
]

EXTRA_WORKFLOW_FIELDS = [
    "date_reported_to_wc","claim_status","froi_sent","osha_301_sent","work_ability_form_sent",
    "restrictions","rtw_job_match","rtw_job_title","rtw_job_description","follow_up_date",
    "adjuster_status","owner","terminal","claim_type","company_avg_days_out","actual_rtw_days",
    "cost_per_day","estimated_days_saved","cost_savings_by_claim","froi_file_link",
    "osha301_file_link","work_ability_file_link",
]

SYNC_BACK_TO_CLAIMS_FIELDS = [
    "claim_number","driver_name","injury_area","injury_description","date_of_injury","claim_stage",
    "work_ability_received","restrictions_summary","next_medical_visit","full_duty_release_date",
    "rtw_tier","temporary_job_assignment","shift_hours","supervisor","rtw_start_date",
    "expected_review_date","adjuster_notified","adjuster_approved","employer_approved",
    "employee_started","current_status","days_injury_to_rtw","plan_active","notes",
    "company_avg_days_out","actual_rtw_days","cost_per_day","estimated_days_saved","cost_savings_by_claim",
]

YES_NO_FIELDS = {
    "work_ability_received","adjuster_notified","adjuster_approved","employer_approved",
    "employee_started","plan_active","froi_sent","osha_301_sent","work_ability_form_sent","rtw_job_match",
}

CHECKLIST_FIELDS = [
    ("froi_sent", "FROI sent"),
    ("osha_301_sent", "OSHA 301 sent"),
    ("work_ability_form_sent", "Work ability form sent"),
    ("work_ability_received", "Work ability received"),
    ("adjuster_notified", "Adjuster notified"),
    ("adjuster_approved", "Adjuster approved"),
    ("employer_approved", "Employer approved"),
    ("temporary_job_assignment", "Temporary job assigned"),
    ("rtw_start_date", "RTW start date set"),
    ("employee_started", "Employee started"),
    ("expected_review_date", "Expected review date set"),
    ("full_duty_release_date", "Full duty release date"),
]

STATUS_OPTIONS = ["", "New", "Waiting on Medical", "Waiting on Approval", "Job Assigned", "RTW Active", "Review Due", "Closed"]
YES_NO_OPTIONS = ["", "No", "Yes"]

RTW_TIER_OPTIONS = [
    "",
    "A – Seated / One-Hand Light Duty",
    "B – Seated/Standing, Keyboard OK",
    "C – Walk/Stand Light",
    "D – Lower Extremity Protected",
    "E – Upper Extremity Protected",
    "F – Cognitive Caution",
    "G – Environmental Restrictions",
    "H – Post-Op / Stable Fractures",
    "I – Vision/Hearing Protected",
    "J – No CMV Driving",
]

TIER_JOB_MAP = {
    "A – Seated / One-Hand Light Duty": [
        "Scan & upload student training records (ELDT portal)",
        "File and organize driver qualification folders (digital)",
        "Review ELDT screenshots for training accuracy",
        "Safety video review (dashcam / training clips)",
        "Captioned training content review",
        "Student attendance log audits",
        "Incident report data entry",
        "Training completion certificate processing",
        "Email-based student follow-ups",
        "Compliance checklist verification",
    ],
    "B – Seated/Standing, Keyboard OK": [
        "Classroom theory instruction (no physical demonstrations)",
        "Simulator observation & scoring",
        "Student test proctoring (written / computer-based)",
        "Training schedule coordination",
        "KPI / completion-rate reporting",
        "Instructor lesson plan updates",
        "Student onboarding sessions (classroom only)",
        "Policy & procedure document updates",
        "Training evaluation scoring",
        "Classroom setup (paper/materials only)",
    ],
    "C – Walk/Stand Light": [
        "Yard walkthroughs (checklist-only observation)",
        "Pre-trip observation (student performs work)",
        "PPE compliance spot checks",
        "Cones / boundary layout supervision (no lifting)",
        "Training area safety inspections",
        "Equipment presence verification (no handling)",
        "End-of-day yard safety checklist completion",
    ],
    "D – Lower Extremity Protected": [
        "Training appointment scheduling",
        "Student call-back confirmations",
        "Instructor coverage coordination",
        "ELDT portal updates",
        "Maintenance issue phone triage",
        "Training supply ordering (online)",
        "Mileage / fuel receipt reconciliation",
        "Training roster updates",
        "Student progress tracking",
        "Email-based compliance communication",
    ],
    "E – Upper Extremity Protected": [
        "Phone-based student support",
        "Radio dispatch (verbal only)",
        "Compliance binder audits",
        "Training records review",
        "Incident timeline documentation",
        "Policy proofreading",
        "Student file quality checks",
        "Scheduling confirmations",
        "Instructor credential tracking",
        "Safety meeting note documentation",
    ],
    "F – Cognitive Caution": [
        "Quiet-room document scanning",
        "Checklist verification tasks",
        "Proofreading training materials",
        "Simple data validation",
        "Attendance cross-checking",
        "Short-duration ELDT audits",
        "Non-time-sensitive admin work",
        "File naming / organization",
        "Training document formatting",
        "Policy acknowledgment tracking",
    ],
    "G – Environmental Restrictions": [
        "Indoor classroom support",
        "ELDT compliance documentation",
        "Training material preparation",
        "Scheduling & admin work",
        "Instructor coordination",
        "Student assessment scoring",
        "Safety documentation updates",
        "Online training support",
        "Policy updates",
        "Remote ELDT assistance (if allowed)",
    ],
    "H – Post-Op / Stable Fractures": [
        "Remote ELDT portal management",
        "Training record audits",
        "Instructor handbook updates",
        "Compliance reporting",
        "Student progress analytics",
        "Online classroom moderation",
        "Training content QA",
        "Incident review write-ups",
        "SOP documentation",
        "Training calendar management",
    ],
    "I – Vision/Hearing Protected": [
        "Captioned training video review",
        "Large-font document audits",
        "Student record verification",
        "Visual checklist completion",
        "Training slide deck updates",
        "Safety talk preparation",
        "Data cleanup with zoom tools",
        "Training photo documentation review",
        "Classroom visual aid preparation",
        "Policy formatting & layout work",
    ],
    "J – No CMV Driving": [
        "All desk-based ELDT tasks",
        "Classroom theory instruction",
        "Simulator proctoring",
        "Yard escort using cart (no driving)",
        "Student observation (passenger seat)",
        "Training documentation oversight",
        "Compliance & audit roles",
        "Instructor mentoring (classroom)",
        "Scheduling & coordination",
        "Safety program administration",
    ],
}

ALL_JOB_OPTIONS = [""] + sorted({job for jobs in TIER_JOB_MAP.values() for job in jobs})


def _safe_str(val):
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def _to_float(val):
    try:
        text = _safe_str(val).replace("$", "").replace(",", "").replace("%", "")
        if text == "":
            return None
        return float(text)
    except Exception:
        return None


def _to_timestamp_or_none(val):
    text = _safe_str(val)
    if text == "":
        return None
    dt = pd.to_datetime(text, errors="coerce")
    return None if pd.isna(dt) else dt


def _to_date_text(val):
    dt = _to_timestamp_or_none(val)
    if dt is None:
        return _safe_str(val)
    return dt.strftime("%Y-%m-%d")


def _to_date_value(val):
    dt = _to_timestamp_or_none(val)
    return None if dt is None else dt.date()


def _fmt_money(val):
    num = _to_float(val)
    if num is None:
        return "-"
    return f"${num:,.0f}"


def _yes_no(val):
    return "Yes" if _safe_str(val).lower() in {"yes", "true", "1"} else "No"


def _all_workflow_fields():
    return RTW_PLAN_CORE_FIELDS + [c for c in EXTRA_WORKFLOW_FIELDS if c not in RTW_PLAN_CORE_FIELDS]


def _blank_workflow_row(company_name=""):
    row = {c: "" for c in _all_workflow_fields()}
    row["company_name"] = company_name
    for c in YES_NO_FIELDS:
        if c in row:
            row[c] = "No"
    row["plan_active"] = "Yes"
    row["current_status"] = "New"
    return row


def _ensure_workflow_columns(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    cols = _all_workflow_fields()
    if df.empty:
        return pd.DataFrame(columns=cols)
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            out[c] = ""
    out["company_name"] = company_name
    for c in cols:
        out[c] = out[c].apply(_safe_str)
    return out[cols]


def _normalize_claims_df(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    needed = list(dict.fromkeys([
        "company_name","claim_number","driver_name","injury_area","injury_description","date_of_injury",
        "claim_stage","claim_status","date_reported_to_wc","terminal","claim_type",
        "company_avg_days_out","actual_rtw_days","cost_per_day","cost_savings_by_claim",
    ] + SYNC_BACK_TO_CLAIMS_FIELDS))
    if df.empty:
        return pd.DataFrame(columns=needed)
    out = df.copy()
    for c in needed:
        if c not in out.columns:
            out[c] = ""
    out["company_name"] = company_name
    for c in needed:
        out[c] = out[c].apply(_safe_str)
    return out[needed]


def _build_from_claims(claims_df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    rows = []
    for _, claim in claims_df.iterrows():
        row = _blank_workflow_row(company_name)
        for c in row.keys():
            if c in claims_df.columns:
                row[c] = _safe_str(claim.get(c, row[c]))
        if row["current_status"] == "":
            row["current_status"] = row.get("claim_stage", "") or "New"
        rows.append(row)
    if not rows:
        rows = [_blank_workflow_row(company_name)]
    return pd.DataFrame(rows)


def _merge_claims_into_workflow(workflow_df: pd.DataFrame, claims_df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    workflow_df = _ensure_workflow_columns(workflow_df, company_name)
    claims_df = _normalize_claims_df(claims_df, company_name)
    if workflow_df.empty:
        return _build_from_claims(claims_df, company_name)

    existing = {_safe_str(r["claim_number"]): r.to_dict() for _, r in workflow_df.iterrows()}
    merged_rows = []
    seen = set()
    for _, claim in claims_df.iterrows():
        claim_number = _safe_str(claim.get("claim_number"))
        row = existing.get(claim_number, _blank_workflow_row(company_name))
        row["company_name"] = company_name
        for c in [
            "claim_number","driver_name","injury_area","injury_description","date_of_injury","claim_stage",
            "claim_status","date_reported_to_wc","terminal","claim_type","company_avg_days_out",
            "actual_rtw_days","cost_per_day","cost_savings_by_claim",
        ]:
            row[c] = _safe_str(claim.get(c, row.get(c, "")))
        merged_rows.append(row)
        seen.add(claim_number)
    for _, row in workflow_df.iterrows():
        claim_number = _safe_str(row.get("claim_number"))
        if claim_number not in seen:
            merged_rows.append(row.to_dict())
    return _ensure_workflow_columns(pd.DataFrame(merged_rows), company_name)


def _calc_derived(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    days_to_rtw, est_days, est_savings = [], [], []
    for _, r in df.iterrows():
        doi = pd.to_datetime(_safe_str(r.get("date_of_injury")), errors="coerce")
        rtw_start = pd.to_datetime(_safe_str(r.get("rtw_start_date")), errors="coerce")
        avg_days = _to_float(r.get("company_avg_days_out"))
        actual_days = _to_float(r.get("actual_rtw_days"))
        cost_per_day = _to_float(r.get("cost_per_day"))
        manual_savings = _to_float(r.get("cost_savings_by_claim"))

        dtr = ""
        if pd.notna(doi) and pd.notna(rtw_start):
            dtr = max((rtw_start - doi).days, 0)
            if actual_days is None:
                actual_days = dtr
        days_to_rtw.append(dtr)

        saved_days = ""
        if avg_days is not None and actual_days is not None:
            saved_days = max(avg_days - actual_days, 0)
        est_days.append(saved_days)

        if manual_savings is not None:
            est_savings.append(manual_savings)
        elif saved_days != "" and cost_per_day is not None:
            est_savings.append(saved_days * cost_per_day)
        else:
            est_savings.append("")
    df["days_injury_to_rtw"] = days_to_rtw
    df["estimated_days_saved"] = est_days
    df["cost_savings_by_claim"] = est_savings
    return df


def _next_action(row):
    checks = [
        ("froi_sent", "Send FROI"),
        ("osha_301_sent", "Send OSHA 301"),
        ("work_ability_form_sent", "Send Work Ability Form"),
        ("work_ability_received", "Receive Work Ability Form"),
        ("adjuster_notified", "Notify Adjuster"),
        ("adjuster_approved", "Get Adjuster Approval"),
        ("employer_approved", "Get Employer Approval"),
        ("rtw_tier", "Set RTW Tier"),
        ("temporary_job_assignment", "Assign Temporary Job"),
        ("rtw_start_date", "Set RTW Start Date"),
        ("employee_started", "Confirm Employee Started"),
        ("expected_review_date", "Set Expected Review Date"),
    ]
    for field, label in checks:
        val = row.get(field, "")
        if field in {"rtw_tier","temporary_job_assignment","rtw_start_date","expected_review_date"}:
            if _safe_str(val) == "":
                return label
        else:
            if _yes_no(val) != "Yes":
                return label
    return "Workflow complete"


def _sync_workflow_back_to_claims(workflow_df: pd.DataFrame, claims_df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    claims_df = _normalize_claims_df(claims_df, company_name)
    if claims_df.empty:
        rows = []
        base_cols = list(dict.fromkeys([
            "company_name","claim_number","driver_name","injury_area","injury_description","date_of_injury",
            "claim_stage","claim_status","date_reported_to_wc","terminal","claim_type","company_avg_days_out",
            "actual_rtw_days","cost_per_day","cost_savings_by_claim",
        ] + SYNC_BACK_TO_CLAIMS_FIELDS))
        for _, w in workflow_df.iterrows():
            row = {c: "" for c in base_cols}
            for c in row.keys():
                if c in workflow_df.columns:
                    row[c] = _safe_str(w.get(c, ""))
            row["company_name"] = company_name
            rows.append(row)
        return pd.DataFrame(rows)

    claims_map = {_safe_str(r["claim_number"]): r.to_dict() for _, r in claims_df.iterrows()}
    for _, w in workflow_df.iterrows():
        claim_number = _safe_str(w.get("claim_number"))
        if claim_number == "":
            continue
        if claim_number not in claims_map:
            claims_map[claim_number] = {c: "" for c in claims_df.columns}
            claims_map[claim_number]["claim_number"] = claim_number
            claims_map[claim_number]["company_name"] = company_name
        row = claims_map[claim_number]
        for c in SYNC_BACK_TO_CLAIMS_FIELDS:
            if c in claims_df.columns:
                row[c] = _safe_str(w.get(c, row.get(c, "")))
        for c in ["driver_name","injury_area","injury_description","date_of_injury","claim_stage","cost_savings_by_claim"]:
            if c in claims_df.columns:
                row[c] = _safe_str(w.get(c, row.get(c, "")))
    out = pd.DataFrame(list(claims_map.values()))
    out["company_name"] = company_name
    for c in out.columns:
        out[c] = out[c].apply(_safe_str)
    return out


def _build_checklist_df(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        completed = 0
        total = len(CHECKLIST_FIELDS)
        missing = []
        for field, label in CHECKLIST_FIELDS:
            val = r.get(field, "")
            if field in {"temporary_job_assignment","rtw_start_date","expected_review_date","full_duty_release_date"}:
                done = _safe_str(val) != ""
            else:
                done = _yes_no(val) == "Yes"
            if done:
                completed += 1
            else:
                missing.append(label)
        rows.append({
            "Claim Number": _safe_str(r.get("claim_number")),
            "Driver": _safe_str(r.get("driver_name")),
            "Checklist Progress": f"{completed}/{total}",
            "Next Missing Item": missing[0] if missing else "Complete",
        })
    return pd.DataFrame(rows)


def _date_editor(label: str, value):
    current = _to_date_value(value)
    selected = st.date_input(label, value=current)
    return "" if selected is None else str(selected)


def _auto_trigger_new_claims_to_rtw_and_claims(company_name: str, claims_df: pd.DataFrame, workflow_df: pd.DataFrame):
    """
    Automation trigger:
    - if new claims exist, ensure RTW plan rows exist automatically
    - calculate derived values
    - sync workflow fields back into claims automatically
    """
    merged = _merge_claims_into_workflow(workflow_df, claims_df, company_name)
    merged = _calc_derived(merged)

    existing_claims = set(claims_df["claim_number"].astype(str).str.strip()) if not claims_df.empty else set()
    existing_workflow = set(workflow_df["claim_number"].astype(str).str.strip()) if not workflow_df.empty else set()
    created = len([c for c in existing_claims if c and c not in existing_workflow])

    synced_claims = _sync_workflow_back_to_claims(merged, claims_df, company_name)
    return merged, synced_claims, created


def show_accident_steps_rtw_workflow():
    st.title("Accident Steps / RTW Workflow")

    company_name = st.session_state.get("company_name", "")
    claims_df = _normalize_claims_df(load_company_rows_from_shared_tab(company_name, CLAIMS_TAB), company_name)
    workflow_df = _ensure_workflow_columns(load_company_rows_from_shared_tab(company_name, WORKFLOW_TAB), company_name)

    workflow_df, auto_synced_claims_df, auto_created = _auto_trigger_new_claims_to_rtw_and_claims(
        company_name, claims_df, workflow_df
    )

    auto_save_col1, auto_save_col2 = st.columns([3, 1])
    with auto_save_col1:
        st.caption("Automation trigger is on: new claims auto-create RTW workflow rows, and key RTW fields are prepared to feed Executive through Claims.")
    with auto_save_col2:
        if st.button("Run Automation Trigger", use_container_width=True):
            save_company_rows_to_shared_tab(workflow_df, company_name, WORKFLOW_TAB)
            save_company_rows_to_shared_tab(auto_synced_claims_df, company_name, CLAIMS_TAB)
            st.success(f"Automation ran. New RTW rows created: {auto_created}. Claims synced for Executive pages.")

    if auto_created > 0:
        st.success(f"{auto_created} new claim(s) were picked up and staged into RTW workflow automatically.")

    st.info("Executive connection: this page now pushes synced RTW fields into Claims, so Executive Overview, Financial Impact, Before vs After, and Premium/Risk can read the updated results.")

    open_claims = int(workflow_df["claim_number"].astype(str).str.strip().ne("").sum())
    waiting_workability = max(
        int(workflow_df["work_ability_form_sent"].astype(str).apply(lambda x: _yes_no(x) == "Yes").sum())
        - int(workflow_df["work_ability_received"].astype(str).apply(lambda x: _yes_no(x) == "Yes").sum()),
        0,
    )
    active_plans = int(workflow_df["plan_active"].astype(str).apply(lambda x: _yes_no(x) == "Yes").sum())
    started = int(workflow_df["employee_started"].astype(str).apply(lambda x: _yes_no(x) == "Yes").sum())
    total_days_saved = pd.to_numeric(workflow_df["estimated_days_saved"], errors="coerce").fillna(0).sum()
    total_savings = pd.to_numeric(workflow_df["cost_savings_by_claim"], errors="coerce").fillna(0).sum()

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Open Claims", open_claims)
    c2.metric("Waiting on Workability", waiting_workability)
    c3.metric("Active Plans", active_plans)
    c4.metric("Employees Started", started)
    c5.metric("Estimated Days Saved", f"{total_days_saved:,.0f}")
    c6.metric("Estimated Savings", _fmt_money(total_savings))

    st.subheader("Executive Feed Check")
    executive_feed_df = workflow_df[[
        "claim_number","driver_name","current_status","days_injury_to_rtw",
        "estimated_days_saved","cost_savings_by_claim","rtw_tier","temporary_job_assignment"
    ]].copy()
    st.dataframe(executive_feed_df, use_container_width=True, hide_index=True)

    st.subheader("RTW Plan Checklist")
    st.dataframe(_build_checklist_df(workflow_df), use_container_width=True, hide_index=True)

    st.subheader("Next Actions")
    actions_df = workflow_df[["claim_number","driver_name","injury_area","claim_stage","current_status"]].copy()
    actions_df["Next Action"] = workflow_df.apply(_next_action, axis=1)
    st.dataframe(actions_df, use_container_width=True, hide_index=True)

    st.subheader("Quick Claim Editor")
    claim_labels = [""] + [
        f'{_safe_str(r.get("claim_number"))} - {_safe_str(r.get("driver_name"))}'
        for _, r in workflow_df.iterrows()
        if _safe_str(r.get("claim_number")) or _safe_str(r.get("driver_name"))
    ]
    selected_label = st.selectbox("Select claim to edit in grouped sections", claim_labels)

    edited_df = workflow_df.copy()
    if selected_label:
        selected_claim = selected_label.split(" - ")[0].strip()
        idxs = edited_df.index[edited_df["claim_number"].astype(str).str.strip() == selected_claim].tolist()
        if idxs:
            idx = idxs[0]
            row = edited_df.loc[idx].copy()

            with st.expander("Claim Info", expanded=True):
                a,b = st.columns(2)
                row["driver_name"] = a.text_input("Driver Name", value=_safe_str(row["driver_name"]))
                row["injury_area"] = b.text_input("Injury Area", value=_safe_str(row["injury_area"]))
                row["injury_description"] = st.text_area("Injury Description", value=_safe_str(row["injury_description"]))
                c,d = st.columns(2)
                row["date_of_injury"] = _date_editor("Date of Injury", row["date_of_injury"])
                cur_status = _safe_str(row["current_status"])
                row["current_status"] = d.selectbox("Current Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(cur_status) if cur_status in STATUS_OPTIONS else 0)

            with st.expander("Medical / Restrictions"):
                a,b = st.columns(2)
                row["work_ability_form_sent"] = a.selectbox("Work Ability Form Sent", YES_NO_OPTIONS, index=YES_NO_OPTIONS.index(_yes_no(row["work_ability_form_sent"])))
                row["work_ability_received"] = b.selectbox("Work Ability Received", YES_NO_OPTIONS, index=YES_NO_OPTIONS.index(_yes_no(row["work_ability_received"])))
                row["restrictions_summary"] = st.text_area("Restrictions Summary", value=_safe_str(row["restrictions_summary"]))
                c,d = st.columns(2)
                row["next_medical_visit"] = _date_editor("Next Medical Visit", row["next_medical_visit"])
                row["full_duty_release_date"] = _date_editor("Full Duty Release Date", row["full_duty_release_date"])

            with st.expander("Approvals"):
                a,b,c = st.columns(3)
                row["adjuster_notified"] = a.selectbox("Adjuster Notified", YES_NO_OPTIONS, index=YES_NO_OPTIONS.index(_yes_no(row["adjuster_notified"])))
                row["adjuster_approved"] = b.selectbox("Adjuster Approved", YES_NO_OPTIONS, index=YES_NO_OPTIONS.index(_yes_no(row["adjuster_approved"])))
                row["employer_approved"] = c.selectbox("Employer Approved", YES_NO_OPTIONS, index=YES_NO_OPTIONS.index(_yes_no(row["employer_approved"])))

            with st.expander("RTW Placement"):
                a,b = st.columns(2)
                cur_tier = _safe_str(row["rtw_tier"])
                row["rtw_tier"] = a.selectbox("RTW Tier", RTW_TIER_OPTIONS, index=RTW_TIER_OPTIONS.index(cur_tier) if cur_tier in RTW_TIER_OPTIONS else 0)
                jobs = [""] + TIER_JOB_MAP.get(row["rtw_tier"], [])
                cur_job = _safe_str(row["temporary_job_assignment"])
                row["temporary_job_assignment"] = b.selectbox("Temporary Job Assignment", jobs, index=jobs.index(cur_job) if cur_job in jobs else 0)
                c1,c2,c3 = st.columns(3)
                row["shift_hours"] = c1.text_input("Shift Hours", value=_safe_str(row["shift_hours"]))
                row["supervisor"] = c2.text_input("Supervisor", value=_safe_str(row["supervisor"]))
                row["rtw_start_date"] = _date_editor("RTW Start Date", row["rtw_start_date"])
                d1,d2 = st.columns(2)
                row["expected_review_date"] = _date_editor("Expected Review Date", row["expected_review_date"])
                row["employee_started"] = d2.selectbox("Employee Started", YES_NO_OPTIONS, index=YES_NO_OPTIONS.index(_yes_no(row["employee_started"])))

            with st.expander("Financial Impact"):
                a,b,c = st.columns(3)
                row["company_avg_days_out"] = a.text_input("Company Avg Days Out", value=_safe_str(row["company_avg_days_out"]))
                row["actual_rtw_days"] = b.text_input("Actual RTW Days", value=_safe_str(row["actual_rtw_days"]))
                row["cost_per_day"] = c.text_input("Cost Per Day", value=_safe_str(row["cost_per_day"]))
                row["notes"] = st.text_area("Notes", value=_safe_str(row["notes"]))

            if st.button("Apply Quick Claim Edit", use_container_width=True):
                for col in edited_df.columns:
                    if col in row.index:
                        edited_df.at[idx, col] = row[col]
                st.success("Quick claim edits applied below. Use Save Workflow Updates or Save + Sync Back to Claims.")

    st.subheader("Full Editable Workflow Grid")
    grid = edited_df.copy()
    for col in ["date_of_injury","date_reported_to_wc","next_medical_visit","full_duty_release_date","rtw_start_date","expected_review_date","follow_up_date"]:
        if col in grid.columns:
            grid[col] = grid[col].apply(_to_date_text)

    grid_df = st.data_editor(
        grid,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "company_name": st.column_config.TextColumn("Company", disabled=True),
            "claim_number": st.column_config.TextColumn("Claim Number"),
            "driver_name": st.column_config.TextColumn("Driver"),
            "injury_area": st.column_config.TextColumn("Injury Area"),
            "injury_description": st.column_config.TextColumn("Injury Description", width="medium"),
            "date_of_injury": st.column_config.TextColumn("Date of Injury"),
            "claim_stage": st.column_config.TextColumn("Claim Stage"),
            "work_ability_received": st.column_config.SelectboxColumn("Work Ability Received", options=YES_NO_OPTIONS),
            "restrictions_summary": st.column_config.TextColumn("Restrictions Summary", width="medium"),
            "next_medical_visit": st.column_config.TextColumn("Next Medical Visit"),
            "full_duty_release_date": st.column_config.TextColumn("Full Duty Release Date"),
            "rtw_tier": st.column_config.SelectboxColumn("RTW Tier", options=RTW_TIER_OPTIONS),
            "temporary_job_assignment": st.column_config.SelectboxColumn("Temporary Job Assignment", options=ALL_JOB_OPTIONS),
            "shift_hours": st.column_config.TextColumn("Shift Hours"),
            "supervisor": st.column_config.TextColumn("Supervisor"),
            "rtw_start_date": st.column_config.TextColumn("RTW Start Date"),
            "expected_review_date": st.column_config.TextColumn("Expected Review Date"),
            "adjuster_notified": st.column_config.SelectboxColumn("Adjuster Notified", options=YES_NO_OPTIONS),
            "adjuster_approved": st.column_config.SelectboxColumn("Adjuster Approved", options=YES_NO_OPTIONS),
            "employer_approved": st.column_config.SelectboxColumn("Employer Approved", options=YES_NO_OPTIONS),
            "employee_started": st.column_config.SelectboxColumn("Employee Started", options=YES_NO_OPTIONS),
            "current_status": st.column_config.SelectboxColumn("Current Status", options=STATUS_OPTIONS),
            "days_injury_to_rtw": st.column_config.NumberColumn("Days Injury to RTW", format="%.1f", disabled=True),
            "plan_active": st.column_config.SelectboxColumn("Plan Active", options=YES_NO_OPTIONS),
            "notes": st.column_config.TextColumn("Notes", width="large"),
            "date_reported_to_wc": st.column_config.TextColumn("Date Reported to WC"),
            "claim_status": st.column_config.TextColumn("Claim Status"),
            "froi_sent": st.column_config.SelectboxColumn("FROI Sent", options=YES_NO_OPTIONS),
            "osha_301_sent": st.column_config.SelectboxColumn("OSHA 301 Sent", options=YES_NO_OPTIONS),
            "work_ability_form_sent": st.column_config.SelectboxColumn("Work Ability Form Sent", options=YES_NO_OPTIONS),
            "restrictions": st.column_config.TextColumn("Restrictions", width="medium"),
            "rtw_job_match": st.column_config.SelectboxColumn("RTW Job Match", options=YES_NO_OPTIONS),
            "rtw_job_title": st.column_config.TextColumn("RTW Job Title"),
            "rtw_job_description": st.column_config.TextColumn("RTW Job Description", width="medium"),
            "follow_up_date": st.column_config.TextColumn("Follow-Up Date"),
            "adjuster_status": st.column_config.TextColumn("Adjuster Status"),
            "owner": st.column_config.TextColumn("Owner"),
            "terminal": st.column_config.TextColumn("Terminal"),
            "claim_type": st.column_config.TextColumn("Claim Type"),
            "company_avg_days_out": st.column_config.NumberColumn("Company Avg Days Out", format="%.1f"),
            "actual_rtw_days": st.column_config.NumberColumn("Actual RTW Days", format="%.1f"),
            "cost_per_day": st.column_config.NumberColumn("Cost Per Day", format="%.2f"),
            "estimated_days_saved": st.column_config.NumberColumn("Estimated Days Saved", format="%.1f", disabled=True),
            "cost_savings_by_claim": st.column_config.NumberColumn("Cost Savings by Claim", format="%.2f"),
            "froi_file_link": st.column_config.TextColumn("FROI File Link", width="medium"),
            "osha301_file_link": st.column_config.TextColumn("OSHA 301 File Link", width="medium"),
            "work_ability_file_link": st.column_config.TextColumn("Work Ability File Link", width="medium"),
        },
    )

    grid_df = _ensure_workflow_columns(grid_df, company_name)
    grid_df["company_name"] = company_name
    grid_df = _calc_derived(grid_df)

    b1,b2,b3,b4 = st.columns(4)
    with b1:
        if st.button("Save Workflow Updates", use_container_width=True):
            save_company_rows_to_shared_tab(grid_df, company_name, WORKFLOW_TAB)
            st.success("RTW workflow saved to Google Sheets.")
    with b2:
        if st.button("Save + Sync Back to Claims", use_container_width=True):
            save_company_rows_to_shared_tab(grid_df, company_name, WORKFLOW_TAB)
            synced_claims = _sync_workflow_back_to_claims(grid_df, claims_df, company_name)
            save_company_rows_to_shared_tab(synced_claims, company_name, CLAIMS_TAB)
            st.success("RTW workflow saved and synced back to Claims. Executive pages now have updated claim feed.")
    with b3:
        if st.button("Reset From Claims Data", use_container_width=True):
            rebuilt = _build_from_claims(claims_df, company_name)
            rebuilt = _calc_derived(rebuilt)
            save_company_rows_to_shared_tab(rebuilt, company_name, WORKFLOW_TAB)
            st.success("Workflow rebuilt from Claims data. Refresh the page.")
    with b4:
        csv_buffer = io.StringIO()
        grid_df.to_csv(csv_buffer, index=False)
        st.download_button("Download RTW Workflow CSV", data=csv_buffer.getvalue(), file_name="18WW_accident_steps_rtw_workflow.csv", mime="text/csv", use_container_width=True)

    st.caption("This page includes automation trigger, checklist guidance, grouped editing, sync-back to Claims, and Executive feed connection.")

def show_rtw_plan():
    show_accident_steps_rtw_workflow()
