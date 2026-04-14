import streamlit as st
from io_layer.session_store import load_session_data
import os
import json
import pandas as pd

import math
try:
    import cv2
except Exception:
    cv2 = None
try:
    import mediapipe as mp
except Exception:
    mp = None
import numpy as np
from PIL import Image, ImageOps
from typing import Dict

from ui.pages.drivers import show_drivers
from ui.pages.claims import show_claims
from ui.pages.rtw_plan import show_rtw_plan
from ui.pages.reports import show_reports
from ui.pages.savings import show_savings
from ui.pages.cost_per_fte_page import render_cost_per_fte_page
from ui.pages.savings_to_date_page import render_savings_to_date_page
from ui.pages.sales_to_pay_page import render_sales_to_pay_page
from ui.pages.lag_time_page import render_lag_time_page
from ui.pages.rtw_ratio_page import render_rtw_ratio_page
from ui.pages.out_of_work_page import render_out_of_work_page
from ui.pages.executive_financial_impact import render_executive_financial_impact
from ui.pages.executive_rtw_dashboard import render_executive_rtw_dashboard
from ui.pages.executive_wc_impact import render_executive_wc_impact
from ui.pages.executive_fms_page import render_executive_fms_dashboard
from ui.pages.executive_overview import render_executive_overview
from ui.pages.rom_mmi_page import render_rom_mmi_page
from ui.pages.executive_rom_mmi_page import render_executive_rom_mmi_page
from ui.pages.saving_rom_mmi_page import render_saving_rom_mmi_page
from ui.pages.accident_steps_rtw_workflow import show_accident_steps_rtw_workflow
from io_layer.google_company_store import (
    load_company_rows_from_shared_tab,
    save_company_rows_to_shared_tab,
)
mp_pose = mp.solutions.pose if mp else None
SUPPORTED_VIEWS = ["front", "side", "back"]

BRAND_NAVY = "#0F1B38"
BRAND_BLUE = "#2563D1"
BRAND_PURPLE = "#6338AA"
BRAND_SILVER = "#EEF1F8"
BRAND_SLATE = "#52606F"
BRAND_RED = (30, 30, 220)
BRAND_BLUE_CV = (210, 120, 40)
BRAND_PURPLE_CV = (170, 95, 130)
BRAND_AMBER_CV = (0, 170, 255)
BRAND_SLATE_CV = (115, 95, 82)

FMS_TAB_NAME = "FMS"
FMS_HISTORY_COLUMNS = [
    "company_name",
    "driver_id",
    "driver_name",
    "assessment_date",
    "session_tag",
    "assessor",
    "front_image_name",
    "side_image_name",
    "back_image_name",
    "front_score",
    "side_score",
    "back_score",
    "total_score",
    "overall_risk",
    "front_findings",
    "side_findings",
    "back_findings",
    "findings_summary",
    "corrective_priorities",
]


# -----------------------------
# UI
# -----------------------------

def show_company_overview(company_name, drivers_df, claims_df):
    st.title(company_name)

    num_drivers = len(drivers_df) if isinstance(drivers_df, pd.DataFrame) else 0
    active_claims = 0

    if isinstance(claims_df, pd.DataFrame) and "current_status" in claims_df.columns:
        active_claims = len(claims_df[claims_df["current_status"] != "Completed"])

    st.subheader(f"{num_drivers} Drivers | {active_claims} Active Claims")

    st.markdown("---")

    rtw_ratio = "N/A"
    avg_rtw_days = "N/A"
    lag_time = "N/A"
    total_cost = "N/A"

    if isinstance(claims_df, pd.DataFrame) and not claims_df.empty:

        if "days_injury_to_rtw" in claims_df.columns:
            valid_rtw = claims_df["days_injury_to_rtw"].dropna()
            if len(valid_rtw) > 0:
                fast = valid_rtw[valid_rtw <= 4]
                rtw_ratio = f"{round(len(fast) / len(valid_rtw) * 100, 1)}%"
                avg_rtw_days = f"{round(valid_rtw.mean(), 1)}"

        if "lag_days" in claims_df.columns:
            valid_lag = claims_df["lag_days"].dropna()
            if len(valid_lag) > 0:
                lag_time = f"{round(valid_lag.mean(), 1)}"

        if "total_cost" in claims_df.columns:
            cost = pd.to_numeric(claims_df["total_cost"], errors="coerce").dropna()
            if len(cost) > 0:
                total_cost = f"${int(cost.sum()):,}"

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("RTW Ratio (≤4 Days)", rtw_ratio)
    col2.metric("Avg RTW Days", avg_rtw_days)
    col3.metric("Lag Time (Days)", lag_time)
    col4.metric("Total Claim Cost", total_cost)

    st.markdown("---")

    st.markdown("**Lag time and delayed return-to-work are the primary drivers of claim cost.**")
    st.markdown("➡️ Let’s look at where this is happening inside your claims.")

def apply_page_style() -> None:
    st.markdown(
        f"""
        <style>
            .block-container {{padding-top: 1.2rem; padding-bottom: 1.2rem;}}
            .metric-card {{background: {BRAND_SILVER}; border: 1px solid #d7ddea; border-radius: 14px; padding: 16px;}}
            .section-card {{background: white; border: 1px solid #E5E7EB; border-radius: 14px; padding: 18px; margin-bottom: 12px;}}
            .pill {{display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700;}}
            .pill-low {{background:#E8F5E9; color:#1B5E20;}}
            .pill-moderate {{background:#FFF3E0; color:#E65100;}}
            .pill-elevated {{background:#FDECE4; color:#C2410C;}}
            .pill-high {{background:#FDECEC; color:#B91C1C;}}
            .small-note {{color:{BRAND_SLATE}; font-size:0.92rem;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    left, right = st.columns([4, 1])
    with left:
        st.markdown(f"<h1 style='margin-bottom:0;color:{BRAND_NAVY};'>18WW FMS / Static Movement Screen</h1>", unsafe_allow_html=True)
        st.markdown(
            "<div class='small-note'>CDL-focused front, side, and back screening page for baseline documentation, corrective planning, and repeat comparison.</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"<div style='background:{BRAND_NAVY};color:white;border-radius:14px;padding:14px;text-align:center;font-weight:700;'>18WW<br><span style='font-size:12px;font-weight:500;'>FMS PAGE</span></div>",
            unsafe_allow_html=True,
        )


def risk_class(score: int) -> str:
    if score <= 3:
        return "low"
    if score <= 7:
        return "moderate"
    if score <= 12:
        return "elevated"
    return "high"


# -----------------------------
# math / landmarks
# -----------------------------

def get_point(landmarks, idx: int, w: int, h: int) -> np.ndarray:
    lm = landmarks[idx]
    return np.array([int(lm.x * w), int(lm.y * h)])


def midpoint(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    return np.array([(p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2])


def line_angle_degrees(p1: np.ndarray, p2: np.ndarray) -> float:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.degrees(math.atan2(dy, dx))


def tilt_from_horizontal_deg(p1: np.ndarray, p2: np.ndarray) -> float:
    angle = abs(line_angle_degrees(p1, p2))
    angle = min(angle, abs(180 - angle))
    return round(angle, 1)


def angle_3pts(a: np.ndarray, b: np.ndarray, c: np.ndarray):
    ba = a - b
    bc = c - b
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    if norm_ba == 0 or norm_bc == 0:
        return None
    cos_angle = np.dot(ba, bc) / (norm_ba * norm_bc)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return round(math.degrees(math.acos(cos_angle)), 1)


def horizontal_distance(p1: np.ndarray, p2: np.ndarray) -> int:
    return int(abs(p1[0] - p2[0]))


def draw_point(img, p, color=(255, 255, 255), radius=5):
    cv2.circle(img, tuple(p), radius, color, -1)


def draw_line(img, p1, p2, color=(255, 255, 255), thickness=2):
    cv2.line(img, tuple(p1), tuple(p2), color, thickness)


def put_text(img, text, p, color=(255, 255, 255), scale=0.52, thickness=2):
    cv2.putText(img, text, (int(p[0]), int(p[1])), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)


def classify_angle_severity(value, minor_low, moderate_low, major_low):
    if value >= major_low:
        return "Major", 3
    if value >= moderate_low:
        return "Moderate", 2
    if value >= minor_low:
        return "Minor", 1
    return None, 0


def classify_distance_severity(value, minor_low, moderate_low, major_low):
    if value >= major_low:
        return "Major", 3
    if value >= moderate_low:
        return "Moderate", 2
    if value >= minor_low:
        return "Minor", 1
    return None, 0


def corrected_ear_anchor_from_ear_and_shoulder(points: Dict[str, np.ndarray], use_left: bool):
    if use_left:
        raw_ear = points["left_ear"]
        shoulder = points["left_shoulder"]
        opposite_shoulder = points["right_shoulder"]
        hip = points["left_hip"]
    else:
        raw_ear = points["right_ear"]
        shoulder = points["right_shoulder"]
        opposite_shoulder = points["left_shoulder"]
        hip = points["right_hip"]

    shoulder_width = max(40, abs(int(opposite_shoulder[0]) - int(shoulder[0])))
    torso_height = max(60, abs(int(hip[1]) - int(shoulder[1])))
    horizontal_sign = 1 if raw_ear[0] >= shoulder[0] else -1

    min_dx = int(round(shoulder_width * 0.10))
    max_dx = int(round(shoulder_width * 0.28))
    raw_dx = abs(int(raw_ear[0]) - int(shoulder[0]))
    target_dx = max(min_dx, min(max_dx, raw_dx if raw_dx > 0 else int(round(shoulder_width * 0.18))))

    target_x = int(shoulder[0] + horizontal_sign * target_dx)
    target_y = int(shoulder[1] - min(int(round(shoulder_width * 0.52)), int(round(torso_height * 0.85))))
    target_anchor = np.array([target_x, target_y])

    corrected = np.array([
        int(round(raw_ear[0] * 0.65 + target_anchor[0] * 0.35)),
        int(round(raw_ear[1] * 0.35 + target_anchor[1] * 0.65)),
    ])

    forward_shift_px = max(2, int(round(shoulder_width * 0.01)))
    upward_shift_px = max(10, int(round(torso_height * 0.08)))
    corrected = np.array([
        int(corrected[0] + horizontal_sign * forward_shift_px),
        int(corrected[1] - upward_shift_px),
    ])
    return corrected, raw_ear, target_anchor


# -----------------------------
# findings
# -----------------------------

def add_finding(findings, view, name, severity, points, metric_name, metric_value, cdl_impact, corrective):
    findings.append(
        {
            "view": view,
            "name": name,
            "severity": severity,
            "points": points,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "cdl_impact": cdl_impact,
            "corrective": corrective,
        }
    )


def analyze_front_view(points: Dict[str, np.ndarray], overlay: np.ndarray):
    findings, metrics, score = [], {}, 0
    le, re = points["left_eye"], points["right_eye"]
    ls, rs = points["left_shoulder"], points["right_shoulder"]
    lh, rh = points["left_hip"], points["right_hip"]
    lk, rk = points["left_knee"], points["right_knee"]
    la, ra = points["left_ankle"], points["right_ankle"]
    lf, rf = points["left_foot_index"], points["right_foot_index"]

    head_tilt = tilt_from_horizontal_deg(le, re)
    metrics["Head tilt (deg)"] = head_tilt
    draw_line(overlay, le, re)
    put_text(overlay, f"Head tilt: {head_tilt}", midpoint(le, re) + np.array([10, -10]), BRAND_BLUE_CV)
    sev, pts = classify_angle_severity(head_tilt, 2.0, 4.0, 7.0)
    if sev:
        draw_line(overlay, le, re, BRAND_RED, 4)
        add_finding(findings, "front", "Head tilt", sev, pts, "Head tilt (deg)", head_tilt,
                    "May reflect asymmetrical neck loading during long driving shifts.",
                    "Cervical mobility and head-position resets")
        score += pts

    shoulder_tilt = tilt_from_horizontal_deg(ls, rs)
    metrics["Shoulder tilt (deg)"] = shoulder_tilt
    draw_line(overlay, ls, rs)
    put_text(overlay, f"Shoulder tilt: {shoulder_tilt}", midpoint(ls, rs) + np.array([10, -10]), BRAND_BLUE_CV)
    sev, pts = classify_angle_severity(shoulder_tilt, 2.0, 4.0, 7.0)
    if sev:
        draw_line(overlay, ls, rs, BRAND_RED, 4)
        add_finding(findings, "front", "Uneven shoulders", sev, pts, "Shoulder tilt (deg)", shoulder_tilt,
                    "Can increase steering-side fatigue and upper trap loading.",
                    "Scapular control, breathing, and thoracic mobility")
        score += pts

    pelvic_tilt = tilt_from_horizontal_deg(lh, rh)
    metrics["Pelvic tilt (deg)"] = pelvic_tilt
    draw_line(overlay, lh, rh)
    put_text(overlay, f"Pelvic tilt: {pelvic_tilt}", midpoint(lh, rh) + np.array([10, -10]), BRAND_BLUE_CV)
    sev, pts = classify_angle_severity(pelvic_tilt, 2.0, 4.0, 7.0)
    if sev:
        draw_line(overlay, lh, rh, BRAND_RED, 4)
        add_finding(findings, "front", "Pelvic tilt / asymmetry", sev, pts, "Pelvic tilt (deg)", pelvic_tilt,
                    "Can add asymmetrical low-back and hip loading in seated driving.",
                    "Hip symmetry work, glute med, and core control")
        score += pts

    left_knee_offset = max(0, lk[0] - lh[0])
    right_knee_offset = max(0, rh[0] - rk[0])
    knee_valgus_metric = max(left_knee_offset, right_knee_offset)
    metrics["Knee valgus screen (px)"] = knee_valgus_metric
    sev, pts = classify_distance_severity(knee_valgus_metric, 10, 20, 35)
    if sev:
        if left_knee_offset > 0:
            draw_line(overlay, lh, lk, BRAND_RED, 4)
        if right_knee_offset > 0:
            draw_line(overlay, rh, rk, BRAND_RED, 4)
        put_text(overlay, f"Knee valgus: {knee_valgus_metric}px", midpoint(lk, rk) + np.array([10, 20]), BRAND_RED)
        add_finding(findings, "front", "Knee valgus tendency", sev, pts, "Knee valgus screen (px)", knee_valgus_metric,
                    "May increase stress during stepping, climbing, and cab entry/exit.",
                    "Single-leg control and glute strength")
        score += pts

    toe_out_metric = max(horizontal_distance(la, lf), horizontal_distance(ra, rf))
    metrics["Toe-out screen (px)"] = toe_out_metric
    sev, pts = classify_distance_severity(toe_out_metric, 20, 35, 50)
    if sev:
        draw_line(overlay, la, lf, BRAND_AMBER_CV, 3)
        draw_line(overlay, ra, rf, BRAND_AMBER_CV, 3)
        put_text(overlay, f"Toe-out: {toe_out_metric}px", midpoint(la, ra) + np.array([10, 35]), BRAND_AMBER_CV)
        add_finding(findings, "front", "Excessive toe-out angle", sev, pts, "Toe-out screen (px)", toe_out_metric,
                    "Can change stepping mechanics and lower-body loading through the day.",
                    "Foot control, ankle mobility, and hip rotation work")
        score += pts

    return findings, metrics, score


def analyze_side_view(points: Dict[str, np.ndarray], overlay: np.ndarray, image_height: int):
    findings, metrics, score = [], {}, 0
    ls, rs = points["left_shoulder"], points["right_shoulder"]
    lh, rh = points["left_hip"], points["right_hip"]
    lk, rk = points["left_knee"], points["right_knee"]
    la, ra = points["left_ankle"], points["right_ankle"]

    use_left = horizontal_distance(ls, lh) <= horizontal_distance(rs, rh)
    if use_left:
        shoulder_pt, hip_pt, knee_pt, ankle_pt = ls, lh, lk, la
        side_used = "Left"
    else:
        shoulder_pt, hip_pt, knee_pt, ankle_pt = rs, rh, rk, ra
        side_used = "Right"

    ear_anchor, raw_ear, target_anchor = corrected_ear_anchor_from_ear_and_shoulder(points, use_left)
    metrics["Side used"] = side_used

    top_ref = np.array([shoulder_pt[0], max(20, shoulder_pt[1] - 140)])
    bot_ref = np.array([shoulder_pt[0], min(image_height - 20, shoulder_pt[1] + 140)])
    draw_line(overlay, top_ref, bot_ref, BRAND_BLUE_CV, 2)
    draw_line(overlay, shoulder_pt, ear_anchor, BRAND_RED, 3)
    draw_point(overlay, ear_anchor, BRAND_PURPLE_CV, 6)
    put_text(overlay, "Adj ear anchor", ear_anchor + np.array([10, -12]), BRAND_PURPLE_CV)

    ear_shoulder_dx = horizontal_distance(ear_anchor, shoulder_pt)
    metrics["Ear-anchor to shoulder (px)"] = ear_shoulder_dx
    put_text(overlay, f"Ear anchor: {ear_shoulder_dx}px", ear_anchor + np.array([10, 16]), BRAND_RED)
    sev, pts = classify_distance_severity(ear_shoulder_dx, 15, 25, 40)
    if sev:
        add_finding(findings, "side", "Forward head posture tendency", sev, pts, "Ear-anchor to shoulder (px)", ear_shoulder_dx,
                    "May increase neck strain and reduce mirror-check comfort on long shifts.",
                    "Deep neck flexor work, thoracic extension, and seat/headrest review")
        score += pts

    shoulder_hip_dx = horizontal_distance(shoulder_pt, hip_pt)
    metrics["Shoulder-to-hip horizontal diff (px)"] = shoulder_hip_dx
    draw_line(overlay, shoulder_pt, hip_pt)
    put_text(overlay, f"Shoulder-hip: {shoulder_hip_dx}px", shoulder_pt + np.array([10, 45]), BRAND_BLUE_CV)
    sev, pts = classify_distance_severity(shoulder_hip_dx, 20, 30, 45)
    if sev:
        add_finding(findings, "side", "Rounded shoulder tendency", sev, pts, "Shoulder-to-hip horizontal diff (px)", shoulder_hip_dx,
                    "May contribute to steering fatigue and upper-back tightness.",
                    "Pec mobility, thoracic extension, scapular retraction")
        score += pts

    trunk_thigh_angle = angle_3pts(shoulder_pt, hip_pt, knee_pt)
    metrics["Trunk-thigh angle (deg)"] = trunk_thigh_angle if trunk_thigh_angle is not None else "N/A"
    if trunk_thigh_angle is not None:
        put_text(overlay, f"Trunk-thigh: {trunk_thigh_angle}", hip_pt + np.array([10, -10]), BRAND_PURPLE_CV)
        if trunk_thigh_angle < 175:
            deviation = 175 - trunk_thigh_angle
            sev, pts = classify_angle_severity(deviation, 3, 7, 12)
            if sev:
                add_finding(findings, "side", "Anterior pelvic tilt tendency", sev, pts, "Trunk-thigh angle (deg)", trunk_thigh_angle,
                            "May add lumbar compression in prolonged seated driving.",
                            "Hip flexor mobility, anterior core, and glute work")
                score += pts
        elif trunk_thigh_angle > 182:
            deviation = trunk_thigh_angle - 182
            sev, pts = classify_angle_severity(deviation, 2, 4, 7)
            if sev:
                add_finding(findings, "side", "Posterior pelvic tilt tendency", sev, pts, "Trunk-thigh angle (deg)", trunk_thigh_angle,
                            "May reduce sitting comfort and add low-back stiffness.",
                            "Hamstring mobility and hinge patterning")
                score += pts

    knee_angle = angle_3pts(hip_pt, knee_pt, ankle_pt)
    metrics["Side-view knee angle (deg)"] = knee_angle if knee_angle is not None else "N/A"
    if knee_angle is not None:
        draw_line(overlay, hip_pt, knee_pt, BRAND_SLATE_CV, 2)
        draw_line(overlay, knee_pt, ankle_pt, BRAND_SLATE_CV, 2)
        put_text(overlay, f"Knee angle: {knee_angle}", knee_pt + np.array([10, -10]), BRAND_PURPLE_CV)
        if knee_angle < 178:
            deviation = 178 - knee_angle
            sev, pts = classify_angle_severity(deviation, 2, 5, 8)
            if sev:
                add_finding(findings, "side", "Knee flexion tendency", sev, pts, "Side-view knee angle (deg)", knee_angle,
                            "May reflect less efficient standing posture and lower-body fatigue.",
                            "Standing resets, calf/hamstring mobility")
                score += pts
        elif knee_angle > 182:
            deviation = knee_angle - 182
            sev, pts = classify_angle_severity(deviation, 2, 4, 7)
            if sev:
                add_finding(findings, "side", "Knee hyperextension tendency", sev, pts, "Side-view knee angle (deg)", knee_angle,
                            "May reduce shock absorption during stepping and walking.",
                            "Soft-knee posture drills and hamstring strength")
                score += pts

    return findings, metrics, score


def analyze_back_view(points: Dict[str, np.ndarray], overlay: np.ndarray):
    findings, metrics, score = [], {}, 0
    ls, rs = points["left_shoulder"], points["right_shoulder"]
    lh, rh = points["left_hip"], points["right_hip"]
    la, ra = points["left_ankle"], points["right_ankle"]
    lheel, rheel = points["left_heel"], points["right_heel"]

    shoulder_tilt = tilt_from_horizontal_deg(ls, rs)
    metrics["Shoulder symmetry tilt (deg)"] = shoulder_tilt
    draw_line(overlay, ls, rs)
    put_text(overlay, f"Shoulder tilt: {shoulder_tilt}", midpoint(ls, rs) + np.array([10, -10]), BRAND_BLUE_CV)
    sev, pts = classify_angle_severity(shoulder_tilt, 2.0, 4.0, 7.0)
    if sev:
        draw_line(overlay, ls, rs, BRAND_RED, 4)
        add_finding(findings, "back", "Uneven shoulders", sev, pts, "Shoulder symmetry tilt (deg)", shoulder_tilt,
                    "Can signal asymmetrical loading through the upper back and neck.",
                    "Scapular symmetry and thoracic mobility")
        score += pts

    pelvic_tilt = tilt_from_horizontal_deg(lh, rh)
    metrics["Pelvic symmetry tilt (deg)"] = pelvic_tilt
    draw_line(overlay, lh, rh)
    put_text(overlay, f"Pelvic tilt: {pelvic_tilt}", midpoint(lh, rh) + np.array([10, -10]), BRAND_BLUE_CV)
    sev, pts = classify_angle_severity(pelvic_tilt, 2.0, 4.0, 7.0)
    if sev:
        draw_line(overlay, lh, rh, BRAND_RED, 4)
        add_finding(findings, "back", "Pelvic tilt / asymmetry", sev, pts, "Pelvic symmetry tilt (deg)", pelvic_tilt,
                    "May contribute to asymmetrical hip and low-back loading.",
                    "Hip symmetry, glute med, and core control")
        score += pts

    rearfoot_metric = max(horizontal_distance(lheel, la), horizontal_distance(rheel, ra))
    metrics["Rearfoot symmetry screen (px)"] = rearfoot_metric
    sev, pts = classify_distance_severity(rearfoot_metric, 10, 18, 28)
    if sev:
        draw_line(overlay, la, lheel, BRAND_AMBER_CV, 3)
        draw_line(overlay, ra, rheel, BRAND_AMBER_CV, 3)
        put_text(overlay, f"Rearfoot: {rearfoot_metric}px", midpoint(la, ra) + np.array([10, 25]), BRAND_AMBER_CV)
        add_finding(findings, "back", "Rearfoot pronation / heel eversion tendency", sev, pts, "Rearfoot symmetry screen (px)", rearfoot_metric,
                    "May change loading through the feet, knees, hips, and low back.",
                    "Foot tripod work, ankle mobility, single-leg balance")
        score += pts

    return findings, metrics, score


# -----------------------------
# pipeline
# -----------------------------

def image_to_bgr(uploaded_file) -> np.ndarray:
    pil_image = Image.open(uploaded_file)
    pil_image = ImageOps.exif_transpose(pil_image)
    pil_image = pil_image.convert("RGB")
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def build_points(lm, w, h) -> Dict[str, np.ndarray]:
    return {
        "nose": get_point(lm, 0, w, h),
        "left_eye": get_point(lm, 2, w, h),
        "right_eye": get_point(lm, 5, w, h),
        "left_ear": get_point(lm, 7, w, h),
        "right_ear": get_point(lm, 8, w, h),
        "left_shoulder": get_point(lm, 11, w, h),
        "right_shoulder": get_point(lm, 12, w, h),
        "left_hip": get_point(lm, 23, w, h),
        "right_hip": get_point(lm, 24, w, h),
        "left_knee": get_point(lm, 25, w, h),
        "right_knee": get_point(lm, 26, w, h),
        "left_ankle": get_point(lm, 27, w, h),
        "right_ankle": get_point(lm, 28, w, h),
        "left_heel": get_point(lm, 29, w, h),
        "right_heel": get_point(lm, 30, w, h),
        "left_foot_index": get_point(lm, 31, w, h),
        "right_foot_index": get_point(lm, 32, w, h),
    }


def analyze_uploaded_image(uploaded_file, view: str):
    if cv2 is None:
        return {"status": "error", "error": "OpenCV is not available in this cloud build."}
    if mp_pose is None:
        return {"status": "error", "error": "MediaPipe is not available in this cloud build."}

    image = image_to_bgr(uploaded_file)
    h, w, _ = image.shape
    overlay = image.copy()

    with mp_pose.Pose(static_image_mode=True, model_complexity=2) as pose:
        results = pose.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if not results.pose_landmarks:
        return {"status": "error", "error": f"No body detected in {view} view."}

    points = build_points(results.pose_landmarks.landmark, w, h)
    for name, p in points.items():
        if not (view == "side" and name in {"left_ear", "right_ear"}):
            draw_point(overlay, p, (255, 255, 255), 4)

    if view == "front":
        findings, metrics, score = analyze_front_view(points, overlay)
    elif view == "side":
        findings, metrics, score = analyze_side_view(points, overlay, h)
    else:
        findings, metrics, score = analyze_back_view(points, overlay)

    return {
        "status": "ok",
        "view": view,
        "score": score,
        "findings": findings,
        "metrics": metrics,
        "overlay_rgb": cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB),
    }


def build_summary(results_by_view: Dict[str, dict]):
    findings = []
    scores = {}
    for view, result in results_by_view.items():
        if result.get("status") == "ok":
            findings.extend(result.get("findings", []))
            scores[view] = result.get("score", 0)

    total_score = sum(scores.values())
    unique_impacts, unique_correctives = [], []
    for f in findings:
        if f["cdl_impact"] not in unique_impacts:
            unique_impacts.append(f["cdl_impact"])
        if f["corrective"] not in unique_correctives:
            unique_correctives.append(f["corrective"])

    return {
        "findings": findings,
        "scores": scores,
        "total_score": total_score,
        "overall_risk": risk_class(total_score),
        "impacts": unique_impacts,
        "correctives": unique_correctives,
    }


def results_dataframe(summary: dict) -> pd.DataFrame:
    rows = []
    for f in summary["findings"]:
        rows.append(
            {
                "View": f["view"].title(),
                "Finding": f["name"],
                "Severity": f["severity"],
                "Metric": f["metric_name"],
                "Value": f["metric_value"],
                "CDL Impact": f["cdl_impact"],
                "Corrective Priority": f["corrective"],
            }
        )
    return pd.DataFrame(rows)


def df_download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# -----------------------------
# page
# -----------------------------

def render_protocol_box() -> None:
    with st.expander("18WW photo setup rules", expanded=False):
        st.markdown(
            """
            - Wear a fitted T-shirt and shorts that clearly show hips and knees.
            - No hoodie, loose sweatshirt, or jacket.
            - Barefoot or thin low-profile socks.
            - Camera at waist to mid-torso height.
            - Front, side, and back views with the whole body in frame.
            - Arms relaxed slightly away from the body.
            - Use the same setup each time for repeat comparison.
            """
        )



def _safe_text(val) -> str:
    if pd.isna(val):
        return ""
    text = str(val).strip()
    return "" if text.lower() in {"none", "nan", "null"} else text


def _get_driver_options_for_fms():
    company_name = st.session_state.get("company_name", "")
    df = st.session_state.get("driver_cleaned_df")
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    driver_df = df.copy()
    if "company_name" in driver_df.columns and company_name and company_name != "ALL":
        driver_df = driver_df[driver_df["company_name"].astype(str).str.strip() == str(company_name).strip()].copy()

    for col in ["driver_name", "driver_id", "company_name", "terminal", "status"]:
        if col not in driver_df.columns:
            driver_df[col] = ""
        driver_df[col] = driver_df[col].apply(_safe_text)

    driver_df = driver_df[driver_df["driver_name"] != ""].copy()
    driver_df = driver_df.drop_duplicates(subset=["driver_name", "driver_id"], keep="first").reset_index(drop=True)
    return driver_df


def _view_findings_text(summary: dict, view_name: str) -> str:
    items = []
    for f in summary.get("findings", []):
        if str(f.get("view", "")).strip().lower() == str(view_name).strip().lower():
            items.append(f"{f['name']} ({f['severity']})")
    return "; ".join(items)


def _fms_history_row(meta: dict, summary: dict) -> pd.DataFrame:
    findings_summary = "; ".join(
        [f"{f['view']}:{f['name']} ({f['severity']})" for f in summary.get("findings", [])]
    )
    corrective_priorities = "; ".join(summary.get("correctives", []))
    scores = summary.get("scores", {})
    row = {
        "company_name": meta.get("company", ""),
        "driver_id": meta.get("driver_id", ""),
        "driver_name": meta.get("driver_name", ""),
        "assessment_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_tag": meta.get("session_tag", ""),
        "assessor": meta.get("assessor", ""),
        "front_image_name": meta.get("front_image_name", ""),
        "side_image_name": meta.get("side_image_name", ""),
        "back_image_name": meta.get("back_image_name", ""),
        "front_score": scores.get("front", 0),
        "side_score": scores.get("side", 0),
        "back_score": scores.get("back", 0),
        "total_score": summary.get("total_score", 0),
        "overall_risk": summary.get("overall_risk", ""),
        "front_findings": _view_findings_text(summary, "front"),
        "side_findings": _view_findings_text(summary, "side"),
        "back_findings": _view_findings_text(summary, "back"),
        "findings_summary": findings_summary,
        "corrective_priorities": corrective_priorities,
    }
    return pd.DataFrame([row], columns=FMS_HISTORY_COLUMNS)


def _load_fms_history(company_name: str) -> pd.DataFrame:
    try:
        hist = load_company_rows_from_shared_tab(company_name, FMS_TAB_NAME)
    except Exception:
        hist = pd.DataFrame(columns=FMS_HISTORY_COLUMNS)

    if hist.empty:
        return pd.DataFrame(columns=FMS_HISTORY_COLUMNS)

    hist = hist.copy()
    for col in FMS_HISTORY_COLUMNS:
        if col not in hist.columns:
            hist[col] = ""
    return hist[FMS_HISTORY_COLUMNS].fillna("")


def _save_fms_history_row(company_name: str, row_df: pd.DataFrame) -> None:
    existing = _load_fms_history(company_name)
    combined = pd.concat([existing, row_df], ignore_index=True)
    save_company_rows_to_shared_tab(combined, company_name, FMS_TAB_NAME)


def main():
    apply_page_style()
    render_header()
    render_protocol_box()

    company_default = st.session_state.get("company_name", "")
    if company_default == "ALL":
        company_default = ""
    drivers_df = _get_driver_options_for_fms()

    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        if not drivers_df.empty:
            driver_labels = ["Manual entry"] + [
                f"{row['driver_name']} | {row['driver_id']}" if row["driver_id"] else row["driver_name"]
                for _, row in drivers_df.iterrows()
            ]
            selected_driver_label = st.selectbox("Driver from company", driver_labels, key="fms_driver_select")
            if selected_driver_label != "Manual entry":
                selected_idx = driver_labels.index(selected_driver_label) - 1
                selected_row = drivers_df.iloc[selected_idx]
                company_default = _safe_text(selected_row.get("company_name", company_default))
                driver_default = _safe_text(selected_row.get("driver_name", ""))
                driver_id_default = _safe_text(selected_row.get("driver_id", ""))
            else:
                driver_default = ""
                driver_id_default = ""
        else:
            st.caption("No loaded driver list found in session. You can still enter driver details manually.")
            driver_default = ""
            driver_id_default = ""

        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1.0, 1.0, 1.0])
        with c1:
            company = st.text_input("Company", value=company_default, key="fms_company_input")
        with c2:
            driver_name = st.text_input("Driver / Employee", value=driver_default, key="fms_driver_input")
        with c3:
            driver_id = st.text_input("Driver ID", value=driver_id_default, key="fms_driver_id_input")
        with c4:
            assessor = st.text_input("Assessor", value="18WW", key="fms_assessor_input")
        with c5:
            session_tag = st.text_input("Session Tag", value="Baseline", key="fms_session_tag_input")
        st.markdown("</div>", unsafe_allow_html=True)

    upload_cols = st.columns(3)
    uploads = {}
    for idx, view in enumerate(SUPPORTED_VIEWS):
        with upload_cols[idx]:
            st.markdown(f"### {view.title()} view")
            uploads[view] = st.file_uploader(
                f"Upload {view} image",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"upload_{view}",
            )

    if st.button("Analyze FMS Screen", type="primary", use_container_width=True):
        missing = [view for view in SUPPORTED_VIEWS if uploads[view] is None]
        if missing:
            st.error(f"Upload all three views first: {', '.join(missing)}")
            st.stop()

        results_by_view = {view: analyze_uploaded_image(uploads[view], view) for view in SUPPORTED_VIEWS}
        errors = [r["error"] for r in results_by_view.values() if r.get("status") == "error"]
        if errors:
            st.error(" | ".join(errors))
            st.stop()

        summary = build_summary(results_by_view)
        st.session_state["fms_results"] = results_by_view
        st.session_state["fms_summary"] = summary
        st.session_state["fms_meta"] = {
            "company": company,
            "driver_name": driver_name,
            "driver_id": driver_id,
            "assessor": assessor,
            "session_tag": session_tag,
            "front_image_name": getattr(uploads.get("front"), "name", ""),
            "side_image_name": getattr(uploads.get("side"), "name", ""),
            "back_image_name": getattr(uploads.get("back"), "name", ""),
        }

    if "fms_summary" not in st.session_state:
        st.info("Upload front, side, and back images, then click Analyze FMS Screen.")
        return

    results_by_view = st.session_state["fms_results"]
    summary = st.session_state["fms_summary"]
    meta = st.session_state["fms_meta"]

    st.markdown("---")
    top1, top2, top3, top4 = st.columns(4)
    with top1:
        st.markdown(f"<div class='metric-card'><div class='small-note'>Company</div><div style='font-size:1.1rem;font-weight:700;color:{BRAND_NAVY};'>{meta['company']}</div></div>", unsafe_allow_html=True)
    with top2:
        driver_label = meta['driver_name'] if not meta.get('driver_id') else f"{meta['driver_name']} ({meta['driver_id']})"
        st.markdown(f"<div class='metric-card'><div class='small-note'>Driver</div><div style='font-size:1.1rem;font-weight:700;color:{BRAND_NAVY};'>{driver_label}</div></div>", unsafe_allow_html=True)
    with top3:
        pill = summary["overall_risk"]
        st.markdown(f"<div class='metric-card'><div class='small-note'>Overall Risk</div><div class='pill pill-{pill}'>{pill.title()}</div><div style='margin-top:10px;font-weight:700;color:{BRAND_NAVY};'>Score {summary['total_score']}</div></div>", unsafe_allow_html=True)
    with top4:
        total_findings = len(summary["findings"])
        st.markdown(f"<div class='metric-card'><div class='small-note'>Findings</div><div style='font-size:1.6rem;font-weight:800;color:{BRAND_NAVY};'>{total_findings}</div><div class='small-note'>{meta['session_tag']} • {meta['assessor']}</div></div>", unsafe_allow_html=True)

    st.markdown("### Findings by View")
    tabs = st.tabs([v.title() for v in SUPPORTED_VIEWS])
    for tab, view in zip(tabs, SUPPORTED_VIEWS):
        result = results_by_view[view]
        with tab:
            left, right = st.columns([1.25, 1])
            with left:
                st.image(result["overlay_rgb"], caption=f"{view.title()} overlay", use_container_width=True)
            with right:
                st.markdown(f"**View score:** {result['score']}")
                if result["findings"]:
                    for f in result["findings"]:
                        st.markdown(
                            f"- **{f['name']}** — {f['severity']}  \\n"
                            f"  {f['metric_name']}: {f['metric_value']}  \\n"
                            f"  CDL impact: {f['cdl_impact']}  \\n"
                            f"  Corrective priority: {f['corrective']}"
                        )
                else:
                    st.success("No major findings recorded on this view.")

                with st.expander("Raw metrics", expanded=False):
                    st.json(result["metrics"])

    st.markdown("### CDL Driver Impact")
    if summary["impacts"]:
        for item in summary["impacts"]:
            st.markdown(f"- {item}")
    else:
        st.write("No major driver-impact flags recorded.")

    st.markdown("### Corrective Priorities")
    if summary["correctives"]:
        for item in summary["correctives"]:
            st.markdown(f"- {item}")
    else:
        st.write("No major corrective priorities recorded.")

    df = results_dataframe(summary)
    st.markdown("### Export Summary")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download FMS summary CSV",
            data=df_download_bytes(df),
            file_name=f"{meta['driver_name'].replace(' ', '_')}_fms_summary.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.write("No finding rows to export.")

    st.markdown("### Save / History")
    save_col, refresh_col = st.columns([1, 1])
    with save_col:
        if st.button("Save FMS to Google Sheets", use_container_width=True, key="fms_save_google_btn"):
            if not meta.get("company"):
                st.error("Company is required before saving.")
            elif not meta.get("driver_name"):
                st.error("Driver name is required before saving.")
            else:
                try:
                    row_df = _fms_history_row(meta, summary)
                    _save_fms_history_row(meta["company"], row_df)
                    st.success(f"Saved FMS result to Google Sheets tab: {FMS_TAB_NAME}")
                except Exception as e:
                    st.error(f"Google save error: {e}")
    with refresh_col:
        if st.button("Refresh Google History", use_container_width=True, key="fms_refresh_google_btn"):
            st.session_state["fms_history_refresh"] = pd.Timestamp.now().isoformat()

    history_df = _load_fms_history(meta.get("company", ""))
    if meta.get("driver_name"):
        history_df = history_df[
            history_df["driver_name"].astype(str).str.strip() == str(meta["driver_name"]).strip()
        ].copy()

    st.markdown("### Driver FMS History")
    if history_df.empty:
        st.caption("No saved Google Sheets history found yet for this driver.")
    else:
        display_cols = [
            "assessment_date", "session_tag", "assessor",
            "front_image_name", "side_image_name", "back_image_name",
            "front_score", "side_score", "back_score",
            "total_score", "overall_risk"
        ]
        st.dataframe(history_df[display_cols], use_container_width=True, hide_index=True)

        latest = history_df.iloc[-1]
        with st.expander("Latest saved findings / priorities", expanded=False):
            st.markdown(f"**Front findings:** {latest.get('front_findings', '')}")
            st.markdown(f"**Side findings:** {latest.get('side_findings', '')}")
            st.markdown(f"**Back findings:** {latest.get('back_findings', '')}")
            st.markdown(f"**Findings summary:** {latest.get('findings_summary', '')}")
            st.markdown(f"**Corrective priorities:** {latest.get('corrective_priorities', '')}")



def render_fms_page():
    main()

USERS_FILE = "users.json"

DEFAULT_USERS = {
    "18wwadmin": {"password": "admin123", "company_name": "ALL", "role": "admin"},
    "jaketrucking": {"password": "test123", "company_name": "JakeTrucking", "role": "client"},
    "abclogistics": {"password": "fleet456", "company_name": "ABC Logistics", "role": "client"},
}

NAV_GROUPS = {
    "Operations": [
        "Company Overview",
        "Drivers",
        "Claims",
        "FMS / Static Screen",
        "Accident Steps / RTW Workflow",
        "RTW",
        "ROM/MMI",
        "Reports",
    ],
    "Executive": [
        "Executive Overview",
        "Executive Business Impact",
        "Executive RTW Dashboard",
        "Executive FMS Dashboard",
        "Executive WC Financial Impact",
        "Executive ROM/MMI",
    ],
    "Savings & Analytics": [
        "Savings",
        "Savings to Date",
        "Cost per FTE",
        "Sales to Pay for Accident",
        "Lag Time",
        "RTW Ratio",
        "Employees Out of Work",
        "Saving ROM/MMI",
    ],
}

ADMIN_GROUP = {
    "Admin": [
        "Export Bundle",
        "Workflow Check / QA",
        "Corrective Plans",
        "Driver Action Summary",
        "Company Action Summary",
        "Terminal Action Summary",
        "ACE / Posture Upload",
        "Merged Data",
        "Executive Report Builder",
    ]
}


def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_USERS, f, indent=2)


def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def create_user(username, password, company_name, role="client"):
    users = load_users()
    username = username.strip().lower()

    if not username:
        return False, "Username is required."
    if username in users:
        return False, "That username already exists."
    if not password:
        return False, "Password is required."
    if not company_name and role != "admin":
        return False, "Company name is required for client users."

    users[username] = {
        "password": password,
        "company_name": "ALL" if role == "admin" else company_name.strip(),
        "role": role,
    }
    save_users(users)
    return True, f"User '{username}' created successfully."


def delete_user(username):
    users = load_users()
    if username == "18wwadmin":
        return False, "Default admin cannot be deleted."
    if username not in users:
        return False, "User not found."

    del users[username]
    save_users(users)
    return True, f"User '{username}' deleted."


def login_screen():
    st.title("18WW Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        users = load_users()
        user = users.get(username.strip().lower())

        if user and user["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username.strip().lower()
            st.session_state["base_company_name"] = user["company_name"]
            st.session_state["company_name"] = user["company_name"]
            st.session_state["role"] = user["role"]

            if user["role"] == "client":
                st.session_state["nav_group_select"] = "Operations"
                st.session_state["nav_page_radio"] = "Company Overview"

            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid username or password")


def require_login():
    # your login logic here
    pass
    
# -----------------------------
# DEMO SAMPLE DATA (CORRECT SPOT)
# -----------------------------
if "demo_loaded" not in st.session_state:
    st.session_state["demo_loaded"] = True

    import pandas as pd

    st.session_state["driver_cleaned_df"] = pd.DataFrame([
        {"company_name": "JakeTrucking", "driver_name": "John Smith"},
        {"company_name": "JakeTrucking", "driver_name": "Mike Johnson"},
        {"company_name": "JakeTrucking", "driver_name": "Chris Lee"},
        {"company_name": "JakeTrucking", "driver_name": "David Brown"},
    ]) 

    require_login()

    # Claims
    st.session_state["claims_cleaned_df"] = pd.DataFrame([
        {
            "company_name": "JakeTrucking",
            "claim_number": "C1001",
            "driver_name": "John Smith",
            "lag_days": 4,
            "actual_rtw_days": 18,
            "cost_per_day": 250,
            "claim_status": "Open",
            "current_status": "Open"
        },
        {
            "company_name": "JakeTrucking",
            "claim_number": "C1002",
            "driver_name": "Mike Johnson",
            "lag_days": 2,
            "actual_rtw_days": 12,
            "cost_per_day": 250,
            "claim_status": "Open",
            "current_status": "Open"
        },
        {
            "company_name": "JakeTrucking",
            "claim_number": "C1003",
            "driver_name": "Chris Lee",
            "lag_days": 6,
            "actual_rtw_days": 22,
            "cost_per_day": 250,
            "claim_status": "Open",
            "current_status": "Open"
        },
    ])

    # Executive numbers
    st.session_state["exec_wc_avoidable_premium"] = 45000
    st.session_state["exec_rtw_fi_financial_drag"] = 30000
    st.session_state["exec_wc_savings_to_date"] = 10000
    st.session_state["exec_rtw_fi_rtw_ratio"] = 35.0
    st.session_state["exec_avg_lag_days"] = 4.0
    st.session_state["exec_employees_out"] = 3
    if not st.session_state.get("logged_in", False):
        login_screen()
        st.stop()
    if "demo_loaded" not in st.session_state:
    st.session_state["demo_loaded"] = True

    # Drivers
    st.session_state["driver_cleaned_df"] = pd.DataFrame([
        {"driver_name": "John Smith"},
        {"driver_name": "Mike Johnson"},
        {"driver_name": "Chris Lee"},
        {"driver_name": "David Brown"},
    ])

    # Claims
    st.session_state["claims_cleaned_df"] = pd.DataFrame([
        {"claim_number": "C1001", "driver_name": "John Smith", "lag_days": 4, "actual_rtw_days": 18, "cost_per_day": 250, "claim_status": "Open"},
        {"claim_number": "C1002", "driver_name": "Mike Johnson", "lag_days": 2, "actual_rtw_days": 12, "cost_per_day": 250, "claim_status": "Open"},
        {"claim_number": "C1003", "driver_name": "Chris Lee", "lag_days": 6, "actual_rtw_days": 22, "cost_per_day": 250, "claim_status": "Open"},
    ])

    # Executive numbers
    st.session_state["exec_wc_avoidable_premium"] = 45000
    st.session_state["exec_rtw_fi_financial_drag"] = 30000
    st.session_state["exec_wc_savings_to_date"] = 10000
    st.session_state["exec_rtw_fi_rtw_ratio"] = 35.0
    st.session_state["exec_avg_lag_days"] = 4.0
    st.session_state["exec_employees_out"] = 3


def logout_button():
    if st.sidebar.button("Log Out"):
        st.session_state.clear()
        st.rerun()


def get_available_companies():
    companies = set()
    possible_keys = [
        "driver_cleaned_df",
        "rom_cleaned_df",
        "rom_scored_df",
        "claims_cleaned_df",
        "merged_driver_rom_df",
    ]
    for key in possible_keys:
        if key in st.session_state:
            df = st.session_state[key]
            if isinstance(df, pd.DataFrame) and not df.empty:
                if "company_name" in df.columns:
                    companies.update(df["company_name"].dropna().astype(str).unique().tolist())
                elif "company" in df.columns:
                    companies.update(df["company"].dropna().astype(str).unique().tolist())

    users = load_users()
    for user in users.values():
        company = user.get("company_name", "")
        if company and company != "ALL":
            companies.add(company)

    return sorted(companies)


def render_admin_switcher():
    if st.session_state.get("role") != "admin":
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("Admin Company Switcher")

    company_options = ["ALL"] + get_available_companies()
    current_company = st.session_state.get("company_name", "ALL")
    if current_company not in company_options:
        current_company = "ALL"

    selected_company = st.sidebar.selectbox(
        "View company",
        company_options,
        index=company_options.index(current_company),
        key="admin_company_switcher",
    )
    st.session_state["company_name"] = selected_company


def render_user_admin_panel():
    if st.session_state.get("role") != "admin":
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("User Management")

    with st.sidebar.expander("Create User", expanded=False):
        new_username = st.text_input("New username", key="new_username")
        new_password = st.text_input("New password", type="password", key="new_password")
        new_company = st.text_input("Company name", key="new_company")
        new_role = st.selectbox("Role", ["client", "admin"], key="new_role")

        if st.button("Create User", key="create_user_btn"):
            success, message = create_user(new_username, new_password, new_company, new_role)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with st.sidebar.expander("Current Users", expanded=False):
        users = load_users()
        for username, user in users.items():
            st.write(f"{username} | {user['role']} | {user['company_name']}")

        delete_username = st.selectbox(
            "Delete user",
            [""] + [u for u in users.keys() if u != "18wwadmin"],
            key="delete_user_select",
        )
        if st.button("Delete Selected User", key="delete_user_btn"):
            if delete_username:
                success, message = delete_user(delete_username)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Select a user first.")


def get_nav_groups():
    if st.session_state.get("role") == "admin":
        groups = dict(NAV_GROUPS)
        groups.update(ADMIN_GROUP)
        return groups
    return NAV_GROUPS


st.set_page_config(page_title="18WW Platform", layout="wide")

ensure_users_file()
require_login()

if "saved_state_autoload_attempted" not in st.session_state:
    try:
        loaded = load_session_data()
        st.session_state["saved_state_loaded_keys"] = list(loaded.keys()) if loaded else []
    except Exception as e:
        st.session_state["saved_state_load_error"] = str(e)
        st.session_state["saved_state_loaded_keys"] = []
    st.session_state["saved_state_autoload_attempted"] = True

st.sidebar.markdown(f"**User:** {st.session_state['username']}")
st.sidebar.markdown(f"**Role:** {st.session_state['role']}")
if st.session_state["role"] == "admin":
    st.sidebar.markdown(f"**Viewing:** {st.session_state['company_name']}")
else:
    st.sidebar.markdown(f"**Company:** {st.session_state['company_name']}")

render_admin_switcher()
render_user_admin_panel()
logout_button()

st.sidebar.title("18WW Navigation")

loaded_keys = st.session_state.get("saved_state_loaded_keys", [])
load_error = st.session_state.get("saved_state_load_error")
if load_error:
    st.sidebar.warning(f"Saved state load error: {load_error}")
elif loaded_keys:
    st.sidebar.success("Saved state loaded")

nav_groups = get_nav_groups()
group_keys = list(nav_groups.keys())

default_group = "Operations" if st.session_state.get("role") == "client" else group_keys[0]
if st.session_state.get("nav_group_select") not in group_keys:
    st.session_state["nav_group_select"] = default_group

selected_group = st.sidebar.selectbox(
    "Section",
    group_keys,
    index=group_keys.index(st.session_state["nav_group_select"]),
    key="nav_group_select",
)

page_options = nav_groups[selected_group]

default_page = "Company Overview" if selected_group == "Operations" and "Company Overview" in page_options else page_options[0]
if st.session_state.get("nav_page_radio") not in page_options:
    st.session_state["nav_page_radio"] = default_page

page = st.sidebar.radio(
    "Go to",
    page_options,
    key="nav_page_radio",
)

st.title("18WW Platform")

if page == "Company Overview":
    drivers_df = st.session_state.get("driver_cleaned_df", pd.DataFrame())
    claims_df = st.session_state.get("claims_cleaned_df", pd.DataFrame())
    company_name = st.session_state.get("company_name", "Demo Company")

    show_company_overview(company_name, drivers_df, claims_df)

elif page == "Drivers":
    show_drivers()
elif page == "Claims":
    show_claims()
elif page == "FMS / Static Screen":
    render_fms_page()
elif page == "Accident Steps / RTW Workflow":
    show_accident_steps_rtw_workflow()
elif page == "RTW":
    show_rtw_plan()
elif page == "ROM/MMI":
    render_rom_mmi_page()
elif page == "Reports":
    show_reports()
elif page == "Executive Overview":
    render_executive_overview()
elif page == "Executive Business Impact":
    render_executive_financial_impact()
elif page == "Executive RTW Dashboard":
    render_executive_rtw_dashboard()
elif page == "Executive FMS Dashboard":
    render_executive_fms_dashboard()
elif page == "Executive WC Financial Impact":
    render_executive_wc_impact()
elif page == "Executive ROM/MMI":
    render_executive_rom_mmi_page()
elif page == "Savings":
    show_savings()
elif page == "Savings to Date":
    render_savings_to_date_page()
elif page == "Cost per FTE":
    render_cost_per_fte_page()
elif page == "Sales to Pay for Accident":
    render_sales_to_pay_page()
elif page == "Lag Time":
    render_lag_time_page()
elif page == "RTW Ratio":
    render_rtw_ratio_page()
elif page == "Employees Out of Work":
    render_out_of_work_page()
elif page == "Saving ROM/MMI":
    render_saving_rom_mmi_page()
