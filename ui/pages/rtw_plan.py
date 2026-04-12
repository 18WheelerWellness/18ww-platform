import streamlit as st
import pandas as pd

from io_layer.google_company_store import (
    load_company_rows_from_shared_tab,
    save_company_rows_to_shared_tab,
)

TAB_NAME = "rtw_plan"

RTW_COLUMNS = [
    "company_name",
    "claim_number",
    "driver_name",
    "injury_area",
    "injury_description",
    "date_of_injury",
    "claim_stage",
    "work_ability_received",
    "restrictions_summary",
    "next_medical_visit",
    "full_duty_release_date",
    "rtw_tier",
    "temporary_job_assignment",
    "shift_hours",
    "supervisor",
    "rtw_start_date",
    "expected_review_date",
    "adjuster_notified",
    "adjuster_approved",
    "employer_approved",
    "employee_started",
    "current_status",
    "days_injury_to_rtw",
    "plan_active",
    "notes",
]

YES_NO = ["No", "Yes"]
CURRENT_STATUS = ["", "Planning", "Pending Approval", "Approved", "Active", "Completed", "On Hold"]

TIER_LABELS = {
    "A": "A – Seated / One-Hand Light Duty",
    "B": "B – Seated/Standing, Keyboard OK",
    "C": "C – Walk/Stand Light",
    "D": "D – Lower Extremity Protected",
    "E": "E – Upper Extremity Protected",
    "F": "F – Cognitive Caution",
    "G": "G – Environmental Restrictions",
    "H": "H – Post-Op / Stable Fractures",
    "I": "I – Vision/Hearing Protected",
    "J": "J – No CMV Driving",
}

TIER_RESTRICTIONS = {
    "A": "Seated as able, no lifting over 5 lb, no climbing, one hand OK, no CMV driving.",
    "B": "Lift ≤10–15 lb, no overhead reach, limited push/pull, keyboard and desk work OK.",
    "C": "Light walk/stand, no ladders, limited lift, no carrying, no uneven ground.",
    "D": "No prolonged walking/standing, minimize stairs and foot controls.",
    "E": "No heavy or repetitive arm use, no forceful grip, shoulder/arm protected.",
    "F": "Simple, low-stimulation tasks only, short-duration focused work.",
    "G": "Indoor-only, avoid heat/cold, fumes, vibration, or dusty environments.",
    "H": "Protected healing phase, seated/light clerical work only unless cleared.",
    "I": "Use enlarged/captioned material, quieter tasks, reduced sensory load.",
    "J": "No CMV driving, all other cleared duties depend on medical restrictions.",
}

TIER_JOBS = {
    "A": [
        "Scan & upload student training records (ELDT portal)",
        "File and organize driver qualification folders (digital)",
        "Review ELD screenshots for training accuracy",
        "Safety video review (dashcam / training clips)",
        "Captioned training content review",
        "Student attendance log audits",
        "Incident report data entry",
        "Training completion certificate processing",
        "Email-based student follow-ups",
        "Compliance checklist verification",
    ],
    "B": [
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
    "C": [
        "Yard walkthroughs (checklist-only observation)",
        "Pre-trip observation (student performs work)",
        "PPE compliance spot checks",
        "Cones / boundary layout supervision (no lifting)",
        "Training area safety inspections",
        "Training area safety inspections",
        "Equipment presence verification (no handling)",
        "Equipment presence verification (no handling)",
        "End-of-day yard safety checklist completion",
    ],
    "D": [
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
    "E": [
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
    "F": [
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
    "G": [
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
    "H": [
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
    "I": [
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
    "J": [
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

def _normalize_yes_no(val) -> str:
    return "Yes" if str(val).strip().lower() in {"yes", "y", "true", "1"} else "No"

def _safe_str(val) -> str:
    if pd.isna(val):
        return ""
    return str(val).strip()

def _extract_tier_code(value: str) -> str:
    value = _safe_str(value)
    if not value:
        return ""
    first = value[0].upper()
    return first if first in TIER_LABELS else ""

def _tier_options():
    return [""] + list(TIER_LABELS.values()) + ["Custom / Add Your Own Tier"]

def _normalize_claims_df(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    if company_name and company_name != "ALL" and "company_name" in df.columns:
        df["company_name"] = company_name

    needed_cols = [
        "company_name",
        "claim_number",
        "driver_name",
        "injury_area",
        "injury_description",
        "date_of_injury",
        "claim_stage",
        "work_ability_received",
    ]
    for col in needed_cols:
        if col not in df.columns:
            df[col] = ""

    df["work_ability_received"] = df["work_ability_received"].apply(_normalize_yes_no)
    return df

def _normalize_workflow_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    for col in ["claim_number", "action_item", "completed"]:
        if col not in df.columns:
            df[col] = ""
    df["completed"] = df["completed"].apply(_normalize_yes_no)
    return df

def _normalize_rtw_df(df: pd.DataFrame, company_name: str) -> pd.DataFrame:
    if df.empty:
        df = pd.DataFrame(columns=RTW_COLUMNS)

    df = df.copy()
    for col in RTW_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    if company_name and company_name != "ALL":
        df["company_name"] = company_name

    for col in [
        "work_ability_received",
        "adjuster_notified",
        "adjuster_approved",
        "employer_approved",
        "employee_started",
        "plan_active",
    ]:
        df[col] = df[col].apply(_normalize_yes_no)

    return df[RTW_COLUMNS].copy()

def _default_plan_from_claim(claim_row: pd.Series, workflow_df: pd.DataFrame, company_name: str, selected_claim: str) -> dict:
    adjuster_notified = "No"
    adjuster_approved = "No"

    if not workflow_df.empty:
        if ((workflow_df["action_item"] == "Adjuster Packet Sent") & (workflow_df["completed"] == "Yes")).any():
            adjuster_notified = "Yes"
        if ((workflow_df["action_item"] == "Adjuster Receipt Confirmed") & (workflow_df["completed"] == "Yes")).any():
            adjuster_approved = "Yes"

    return {
        "company_name": company_name if company_name != "ALL" else _safe_str(claim_row.get("company_name", "")),
        "claim_number": selected_claim,
        "driver_name": _safe_str(claim_row.get("driver_name", "")),
        "injury_area": _safe_str(claim_row.get("injury_area", "")),
        "injury_description": _safe_str(claim_row.get("injury_description", "")),
        "date_of_injury": _safe_str(claim_row.get("date_of_injury", "")),
        "claim_stage": _safe_str(claim_row.get("claim_stage", "")),
        "work_ability_received": _normalize_yes_no(claim_row.get("work_ability_received", "No")),
        "restrictions_summary": "",
        "next_medical_visit": "",
        "full_duty_release_date": "",
        "rtw_tier": "",
        "temporary_job_assignment": "",
        "shift_hours": "",
        "supervisor": "",
        "rtw_start_date": "",
        "expected_review_date": "",
        "adjuster_notified": adjuster_notified,
        "adjuster_approved": adjuster_approved,
        "employer_approved": "No",
        "employee_started": "No",
        "current_status": "Planning",
        "days_injury_to_rtw": "",
        "plan_active": "Yes",
        "notes": "",
    }

def _compute_days_injury_to_rtw(date_of_injury: str, rtw_start_date: str) -> str:
    try:
        doi = pd.to_datetime(date_of_injury, errors="coerce")
        rtw = pd.to_datetime(rtw_start_date, errors="coerce")
        if pd.isna(doi) or pd.isna(rtw):
            return ""
        return str((rtw - doi).days)
    except Exception:
        return ""

def _upsert_plan_row(existing_df: pd.DataFrame, row: dict, company_name: str, selected_claim: str) -> pd.DataFrame:
    df = existing_df.copy()
    if df.empty:
        return pd.DataFrame([row], columns=RTW_COLUMNS)

    mask = df["claim_number"].astype(str) == str(selected_claim)
    if company_name != "ALL" and "company_name" in df.columns:
        mask = mask & (df["company_name"].astype(str) == str(company_name))

    if mask.any():
        idx = df[mask].index[0]
        for col in RTW_COLUMNS:
            df.loc[idx, col] = row.get(col, "")
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    return df[RTW_COLUMNS].copy()

def show_rtw_plan():
    st.title("RTW Plan")
    st.caption("RTW Tier uses your A–J list. Temporary Job Assignment now drops down the jobs tied to that selected letter, with a custom type-in option at the bottom.")

    company_name = st.session_state.get("company_name", "")
    is_all_view = str(company_name).strip().upper() == "ALL"
    if is_all_view:
        st.warning("Admin ALL view is read-only. Select a specific company in the sidebar to create or edit an RTW plan.")

    claims_df = load_company_rows_from_shared_tab(company_name, "claims")
    claims_df = _normalize_claims_df(claims_df, company_name)

    if claims_df.empty or "claim_number" not in claims_df.columns:
        st.warning("No claims found. Add claims first.")
        return

    claim_numbers = sorted(set([c for c in claims_df["claim_number"].fillna("").astype(str).tolist() if c.strip()]))
    selected_claim = st.selectbox("Select Claim Number", claim_numbers)

    claim_matches = claims_df[claims_df["claim_number"].astype(str) == str(selected_claim)]
    claim_row = claim_matches.iloc[0] if not claim_matches.empty else pd.Series(dtype=object)

    workflow_df = load_company_rows_from_shared_tab(company_name, "claims_adjuster_communication")
    workflow_df = _normalize_workflow_df(workflow_df)
    if not workflow_df.empty:
        workflow_df = workflow_df[workflow_df["claim_number"].astype(str) == str(selected_claim)]

    rtw_df = load_company_rows_from_shared_tab(company_name, TAB_NAME)
    rtw_df = _normalize_rtw_df(rtw_df, company_name)

    plan_matches = pd.DataFrame()
    if not rtw_df.empty:
        plan_matches = rtw_df[rtw_df["claim_number"].astype(str) == str(selected_claim)]

    if plan_matches.empty:
        plan = _default_plan_from_claim(claim_row, workflow_df, company_name, selected_claim)
    else:
        plan = plan_matches.iloc[0].to_dict()

    st.subheader("Claim Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Claim Number", _safe_str(plan.get("claim_number", "")))
    c2.metric("Driver", _safe_str(plan.get("driver_name", "")))
    c3.metric("Injury Area", _safe_str(plan.get("injury_area", "")))
    c4.metric("Claim Stage", _safe_str(plan.get("claim_stage", "")))
    st.write(_safe_str(plan.get("injury_description", "")))

    tier_options = _tier_options()
    selected_tier_default = _safe_str(plan.get("rtw_tier", ""))
    if selected_tier_default and selected_tier_default not in tier_options and _extract_tier_code(selected_tier_default) in TIER_LABELS:
        selected_tier_default = TIER_LABELS[_extract_tier_code(selected_tier_default)]
    if selected_tier_default not in tier_options:
        selected_tier_default = ""

    with st.form("rtw_plan_form"):
        st.subheader("Medical / Restrictions")
        m1, m2 = st.columns(2)
        with m1:
            work_ability_received = st.selectbox(
                "Work Ability Received?",
                YES_NO,
                index=YES_NO.index(_normalize_yes_no(plan.get("work_ability_received", "No"))),
            )
            restrictions_summary_input = st.text_area(
                "Restrictions Summary",
                value=_safe_str(plan.get("restrictions_summary", "")),
            )
            next_medical_visit = st.text_input("Next Medical Visit", value=_safe_str(plan.get("next_medical_visit", "")))
        with m2:
            full_duty_release_date = st.text_input("Full Duty Release Date", value=_safe_str(plan.get("full_duty_release_date", "")))
            claim_stage = st.text_input("Claim Stage", value=_safe_str(plan.get("claim_stage", "")))
            date_of_injury = st.text_input("Date of Injury", value=_safe_str(plan.get("date_of_injury", "")))

        st.subheader("RTW Tier + Temporary Job")
        t1, t2 = st.columns(2)
        with t1:
            selected_tier_option = st.selectbox(
                "RTW Tier",
                tier_options,
                index=tier_options.index(selected_tier_default),
            )
            custom_tier = ""
            if selected_tier_option == "Custom / Add Your Own Tier":
                custom_tier = st.text_input("Type Your Own RTW Tier", value="")

        final_tier = custom_tier if selected_tier_option == "Custom / Add Your Own Tier" else selected_tier_option
        tier_code = _extract_tier_code(final_tier)

        with t2:
            if tier_code:
                st.caption("Tier Restrictions / Capabilities")
                st.write(TIER_RESTRICTIONS.get(tier_code, ""))
            else:
                st.caption("Choose a tier to view restrictions / capabilities.")

        auto_restrictions = TIER_RESTRICTIONS.get(tier_code, "")
        restrictions_summary = restrictions_summary_input if restrictions_summary_input.strip() else auto_restrictions

        jobs_for_tier = TIER_JOBS.get(tier_code, [])
        st.caption("Temporary Job Assignment options for selected tier")
        if jobs_for_tier:
            st.write(", ".join(jobs_for_tier))
        else:
            st.write("No built-in jobs for this tier yet. You can type your own below.")

        existing_job = _safe_str(plan.get("temporary_job_assignment", ""))
        job_options = [""] + jobs_for_tier + ["Custom / Type My Own"]
        default_job_option = existing_job if existing_job in job_options else ("Custom / Type My Own" if existing_job else "")

        j1, j2 = st.columns(2)
        with j1:
            selected_job_option = st.selectbox(
                "Temporary Job Assignment",
                job_options,
                index=job_options.index(default_job_option) if default_job_option in job_options else 0,
            )
        with j2:
            typed_custom_job = st.text_input(
                "Type Your Own Temporary Job",
                value=existing_job if default_job_option == "Custom / Type My Own" else "",
            )

        final_job_assignment = typed_custom_job if selected_job_option == "Custom / Type My Own" else selected_job_option

        st.subheader("RTW Plan Details")
        p1, p2 = st.columns(2)
        with p1:
            shift_hours = st.text_input("Shift / Hours", value=_safe_str(plan.get("shift_hours", "")))
            supervisor = st.text_input("Supervisor", value=_safe_str(plan.get("supervisor", "")))
            rtw_start_date = st.text_input("RTW Start Date", value=_safe_str(plan.get("rtw_start_date", "")))
        with p2:
            expected_review_date = st.text_input("Expected Review Date", value=_safe_str(plan.get("expected_review_date", "")))
            current_status = st.selectbox(
                "Current Status",
                CURRENT_STATUS,
                index=CURRENT_STATUS.index(_safe_str(plan.get("current_status", ""))) if _safe_str(plan.get("current_status", "")) in CURRENT_STATUS else 0,
            )
            plan_active = st.selectbox(
                "Plan Active?",
                YES_NO,
                index=YES_NO.index(_normalize_yes_no(plan.get("plan_active", "Yes"))),
            )

        st.subheader("Approval / Communication")
        a1, a2 = st.columns(2)
        with a1:
            adjuster_notified = st.selectbox("Adjuster Notified?", YES_NO, index=YES_NO.index(_normalize_yes_no(plan.get("adjuster_notified", "No"))))
            adjuster_approved = st.selectbox("Adjuster Approved?", YES_NO, index=YES_NO.index(_normalize_yes_no(plan.get("adjuster_approved", "No"))))
        with a2:
            employer_approved = st.selectbox("Employer Approved?", YES_NO, index=YES_NO.index(_normalize_yes_no(plan.get("employer_approved", "No"))))
            employee_started = st.selectbox("Employee Started?", YES_NO, index=YES_NO.index(_normalize_yes_no(plan.get("employee_started", "No"))))

        st.subheader("Outcome Tracking")
        notes = st.text_area("Notes / Follow-Up", value=_safe_str(plan.get("notes", "")))

        save_clicked = st.form_submit_button("Save RTW Plan", disabled=is_all_view)

    days_injury_to_rtw = _compute_days_injury_to_rtw(date_of_injury, rtw_start_date)

    k1, k2, k3 = st.columns(3)
    k1.metric("Work Ability Received", work_ability_received)
    k2.metric("Adjuster Approved", adjuster_approved)
    k3.metric("Days Injury to RTW", days_injury_to_rtw or "-")

    if save_clicked:
        row = {
            "company_name": _safe_str(plan.get("company_name", "")) if is_all_view else company_name,
            "claim_number": selected_claim,
            "driver_name": _safe_str(plan.get("driver_name", "")),
            "injury_area": _safe_str(plan.get("injury_area", "")),
            "injury_description": _safe_str(plan.get("injury_description", "")),
            "date_of_injury": date_of_injury,
            "claim_stage": claim_stage,
            "work_ability_received": work_ability_received,
            "restrictions_summary": restrictions_summary,
            "next_medical_visit": next_medical_visit,
            "full_duty_release_date": full_duty_release_date,
            "rtw_tier": final_tier,
            "temporary_job_assignment": final_job_assignment,
            "shift_hours": shift_hours,
            "supervisor": supervisor,
            "rtw_start_date": rtw_start_date,
            "expected_review_date": expected_review_date,
            "adjuster_notified": adjuster_notified,
            "adjuster_approved": adjuster_approved,
            "employer_approved": employer_approved,
            "employee_started": employee_started,
            "current_status": current_status,
            "days_injury_to_rtw": days_injury_to_rtw,
            "plan_active": plan_active,
            "notes": notes,
        }

        updated_df = _upsert_plan_row(rtw_df, row, company_name, selected_claim)
        save_company_rows_to_shared_tab(updated_df, company_name, TAB_NAME)
        st.success("RTW Plan saved.")
        st.rerun()

    st.subheader("Adjuster Communication Snapshot")
    if workflow_df.empty:
        st.info("No claims adjuster communication steps found for this claim yet.")
    else:
        show_cols = [c for c in ["phase", "step_number", "action_item", "completed"] if c in workflow_df.columns]
        st.dataframe(workflow_df[show_cols], width="stretch", hide_index=True)
    st.subheader("Adjuster Communication Snapshot")
    if workflow_df.empty:
        st.info("No claims adjuster communication steps found for this claim yet.")
    else:
        show_cols = [c for c in ["phase", "step_number", "action_item", "completed"] if c in workflow_df.columns]
        st.dataframe(workflow_df[show_cols], width="stretch", hide_index=True)
