import streamlit as st
import pandas as pd
import random

# =============================
# DEMO DATA GENERATOR (FIXED)
# =============================
def generate_demo_data(fleet_size):
    company_name = st.session_state.get("company_name", "Demo Company")

    if fleet_size == "Small (10)":
        num_drivers = 10
        claim_rate = 0.15
    elif fleet_size == "Medium (50)":
        num_drivers = 50
        claim_rate = 0.20
    else:
        num_drivers = 150
        claim_rate = 0.25

    drivers = []
    claims = []

    for i in range(num_drivers):
        name = f"Driver {i+1}"

        drivers.append({
            "company_name": company_name,
            "driver_name": name
        })

        if random.random() < claim_rate:
            lag = random.randint(2, 7)
            rtw = random.randint(10, 25)

            claims.append({
                "company_name": company_name,
                "claim_number": f"C{i+1000}",
                "driver_name": name,
                "lag_days": lag,
                "actual_rtw_days": rtw,
                "cost_per_day": 250,
                "current_status": "Open"
            })

    return pd.DataFrame(drivers), pd.DataFrame(claims)


# =============================
# LOGIN SYSTEM
# =============================
DEFAULT_USERS = {
    "18wwadmin": {"password": "admin123", "company_name": "ALL", "role": "admin"},
    "jaketrucking": {"password": "test123", "company_name": "JakeTrucking", "role": "client"},
    "abclogistics": {"password": "fleet456", "company_name": "ABC Logistics", "role": "client"},
}

def login_screen():
    st.title("18WW Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Log In"):
        user = DEFAULT_USERS.get(username.strip().lower())

        if user and user["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["company_name"] = user["company_name"]
            st.session_state["role"] = user["role"]

            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid login")


def require_login():
    if not st.session_state.get("logged_in"):
        login_screen()
        st.stop()


# =============================
# APP START
# =============================
st.set_page_config(page_title="18WW Platform", layout="wide")

require_login()

# =============================
# DEMO LOADER (FIXED)
# =============================
fleet_size = st.session_state.get("demo_fleet_size", "Medium (50)")

if (
    "demo_loaded" not in st.session_state
    or st.session_state.get("last_fleet") != fleet_size
):
    drivers_df, claims_df = generate_demo_data(fleet_size)

    st.session_state["driver_cleaned_df"] = drivers_df
    st.session_state["claims_cleaned_df"] = claims_df

    total_claim_cost = len(claims_df) * 5000
    savings = int(total_claim_cost * 0.25)

    st.session_state["exec_wc_avoidable_premium"] = total_claim_cost
    st.session_state["exec_rtw_fi_financial_drag"] = int(total_claim_cost * 0.6)
    st.session_state["exec_wc_savings_to_date"] = savings
    st.session_state["exec_rtw_fi_rtw_ratio"] = 35.0
    st.session_state["exec_avg_lag_days"] = claims_df["lag_days"].mean() if not claims_df.empty else 0
    st.session_state["exec_employees_out"] = len(claims_df)

    st.session_state["last_fleet"] = fleet_size
    st.session_state["demo_loaded"] = True


# =============================
# SIDEBAR (FIXED)
# =============================
username = st.session_state.get("username", "Demo User")
company = st.session_state.get("company_name", "Demo Company")
role = st.session_state.get("role", "admin")

st.sidebar.markdown(f"**User:** {username}")

if role == "admin":
    st.sidebar.markdown(f"**Viewing:** {company}")
else:
    st.sidebar.markdown(f"**Company:** {company}")

# =============================
# DEMO CONTROLS
# =============================
st.sidebar.markdown("---")
st.sidebar.subheader("Demo Controls")

fleet_size = st.sidebar.selectbox(
    "Fleet Size",
    ["Small (10)", "Medium (50)", "Large (150)"],
    key="demo_fleet_size"
)

# =============================
# NAVIGATION (CLEAN)
# =============================
NAV_GROUPS = {
    "Operations": ["Company Overview", "Drivers", "Claims", "RTW"],
    "Executive": ["Executive Overview"],
}

selected_group = st.sidebar.selectbox("Section", list(NAV_GROUPS.keys()))
page = st.sidebar.radio("Go to", NAV_GROUPS[selected_group])

# =============================
# ROUTING
# =============================
st.title("18WW Platform")

drivers_df = st.session_state.get("driver_cleaned_df", pd.DataFrame())
claims_df = st.session_state.get("claims_cleaned_df", pd.DataFrame())

if page == "Company Overview":
    st.title(company)
    st.write(f"{len(drivers_df)} Drivers")
    st.write(f"{len(claims_df)} Claims")

elif page == "Drivers":
    st.dataframe(drivers_df)

elif page == "Claims":
    st.dataframe(claims_df)

elif page == "RTW":
    st.write("RTW Page")

elif page == "Executive Overview":
    st.metric("Total Claims", len(claims_df))
