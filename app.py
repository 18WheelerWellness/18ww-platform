import streamlit as st
import pandas as pd
import random
import json
import os

# -----------------------------
# IMPORT YOUR REAL PAGES
# -----------------------------
from ui.pages.drivers import show_drivers
from ui.pages.claims import show_claims
from ui.pages.rtw_plan import show_rtw_plan
from ui.pages.executive_overview import render_executive_overview

# -----------------------------
# USER SYSTEM
# -----------------------------
USERS_FILE = "users.json"

DEFAULT_USERS = {
    "18wwadmin": {"password": "admin123", "company_name": "ALL", "role": "admin"},
    "jaketrucking": {"password": "test123", "company_name": "JakeTrucking", "role": "client"},
}

def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump(DEFAULT_USERS, f)

def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r") as f:
        return json.load(f)

# -----------------------------
# LOGIN
# -----------------------------
def login_screen():
    st.title("18WW Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    demo_company = st.text_input("Company Name (for demo)")

    if st.button("Log In"):
        users = load_users()
        user = users.get(username.strip().lower())

        if user and user["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = user["role"]

            if demo_company:
                st.session_state["company_name"] = demo_company
            else:
                st.session_state["company_name"] = user["company_name"]

            st.session_state["demo_loaded"] = False
            st.rerun()
        else:
            st.error("Invalid login")

def require_login():
    if not st.session_state.get("logged_in"):
        login_screen()
        st.stop()

# -----------------------------
# DEMO DATA
# -----------------------------
def generate_demo_data(fleet_size):
    if fleet_size == "Small":
        num = 10
        rate = 0.15
    elif fleet_size == "Medium":
        num = 50
        rate = 0.2
    else:
        num = 150
        rate = 0.25

    company = st.session_state.get("company_name")

    drivers = []
    claims = []

    for i in range(num):
        name = f"Driver {i+1}"

        drivers.append({
            "company_name": company,
            "driver_name": name
        })

        if random.random() < rate:
            claims.append({
                "company_name": company,
                "claim_number": f"C{i+1000}",
                "driver_name": name,
                "lag_days": random.randint(2, 7),
                "actual_rtw_days": random.randint(10, 25),
                "cost_per_day": 250,
                "current_status": "Open"
            })

    return pd.DataFrame(drivers), pd.DataFrame(claims)

# -----------------------------
# COMPANY OVERVIEW
# -----------------------------
def show_company_overview():
    company = st.session_state.get("company_name")
    drivers = st.session_state.get("drivers_df", pd.DataFrame())
    claims = st.session_state.get("claims_df", pd.DataFrame())

    st.title(company)
    st.subheader(f"{len(drivers)} Drivers | {len(claims)} Claims")

# -----------------------------
# APP START
# -----------------------------
st.set_page_config(layout="wide")

ensure_users_file()
require_login()

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.markdown(f"User: {st.session_state.get('username')}")
st.sidebar.markdown(f"Company: {st.session_state.get('company_name')}")

if st.sidebar.button("Log Out"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")

# -----------------------------
# FLEET SIZE
# -----------------------------
fleet_size = st.sidebar.selectbox(
    "Fleet Size",
    ["Small", "Medium", "Large"],
    key="fleet_size_select"
)

# -----------------------------
# NAV GROUPS (DROPDOWN SYSTEM)
# -----------------------------
nav_groups = {
    "Operations": ["Overview", "Drivers", "Claims", "RTW"],
    "Executive": ["Executive Overview"]
}

# -----------------------------
# SELECT SECTION
# -----------------------------
selected_group = st.sidebar.selectbox(
    "Section",
    list(nav_groups.keys()),
    key="nav_group_select"
)

# -----------------------------
# PAGE SELECTOR
# -----------------------------
page = st.sidebar.radio(
    "Go to",
    nav_groups[selected_group],
    key="nav_page_select"
)

# -----------------------------
# DATA LOADER
# -----------------------------
if (
    "demo_loaded" not in st.session_state
    or st.session_state.get("last_fleet") != fleet_size
    or st.session_state.get("last_company") != st.session_state.get("company_name")
):

    drivers, claims = generate_demo_data(fleet_size)

    st.session_state["drivers_df"] = drivers
    st.session_state["claims_df"] = claims

    # bridge to existing pages
    st.session_state["driver_cleaned_df"] = drivers
    st.session_state["claims_cleaned_df"] = claims

    st.session_state["last_fleet"] = fleet_size
    st.session_state["last_company"] = st.session_state.get("company_name")
    st.session_state["demo_loaded"] = True

# -----------------------------
# ROUTING
# -----------------------------
if page == "Overview":
    show_company_overview()

elif page == "Drivers":
    show_drivers()

elif page == "Claims":
    show_claims()

elif page == "RTW":
    show_rtw_plan()

elif page == "Executive Overview":
    render_executive_overview()
