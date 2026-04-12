import io
import math
from typing import Dict, List, Tuple

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image


mp_pose = mp.solutions.pose
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


# -----------------------------
# UI
# -----------------------------

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
    pil_image = Image.open(uploaded_file).convert("RGB")
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


def main():
    st.set_page_config(page_title="18WW FMS Page", page_icon="📋", layout="wide")
    apply_page_style()
    render_header()
    render_protocol_box()

    with st.container():
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1.3, 1.3, 1.3, 1])
        with c1:
            company = st.text_input("Company", value="18WW Demo Fleet")
        with c2:
            driver_name = st.text_input("Driver / Employee", value="Driver 001")
        with c3:
            assessor = st.text_input("Assessor", value="18WW")
        with c4:
            session_tag = st.text_input("Session Tag", value="Baseline")
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
            "assessor": assessor,
            "session_tag": session_tag,
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
        st.markdown(f"<div class='metric-card'><div class='small-note'>Driver</div><div style='font-size:1.1rem;font-weight:700;color:{BRAND_NAVY};'>{meta['driver_name']}</div></div>", unsafe_allow_html=True)
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


if __name__ == "__main__":
    main()


def render_fms_page():
    main()
