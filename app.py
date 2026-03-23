import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="ILGA Bill Tracker", layout="wide")

st.title("🏛️ Illinois General Assembly Bill Tracker")

def format_position(pos):
    """Color-code position with emoji indicators."""
    p = str(pos).strip().lower()
    if p == "core bill":
        return "🟢 Core Bill"
    elif p == "support":
        return "🟢 Support"
    elif p == "oppose":
        return "🔴 Oppose"
    elif p == "monitor":
        return "🟡 Monitor"
    return pos


def render_bill_table(csv_path):
    """Load a bill CSV and render it as a Streamlit dataframe."""
    df = pd.read_csv(csv_path)
    today = datetime.now().date()
    df["Action Date"] = pd.to_datetime(df["Action Date"])
    df["Days Since Action"] = df["Action Date"].apply(
        lambda d: (today - d.date()).days if pd.notna(d) else None
    )
    df["Action Date"] = df["Action Date"].dt.strftime("%Y-%m-%d")
    df["Position"] = df["Position"].apply(format_position)

    st.dataframe(
        df,
        column_config={
            "LegiScan Link": st.column_config.LinkColumn("View on LegiScan"),
            "Days Since Action": st.column_config.NumberColumn(
                "Days Since Action",
                help="Number of days since the last recorded action on this bill",
            ),
        },
        hide_index=True,
        use_container_width=True,
    )


# --- Last Checked Timestamp ---
time_file = "last_checked.txt"
data_file = "bills_data.csv"
monitored_file = "monitored_bills_data.csv"

try:
    if os.path.exists(time_file):
        timestamp = os.path.getmtime(time_file)
    else:
        timestamp = os.path.getmtime(data_file)

    utc_time = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC"))
    local_time = utc_time.astimezone(ZoneInfo("America/Chicago"))
    formatted_time = local_time.strftime("%B %d, %Y at %I:%M %p %Z")
    st.markdown(f"**System last checked for updates:** {formatted_time}")
except FileNotFoundError:
    pass

# --- Tracked Bills Table ---
if os.path.exists(data_file):
    render_bill_table(data_file)
else:
    st.markdown("This dashboard tracks target bills and automatically updates daily.")
    st.warning("Data file not found. Wait for the background script to run or trigger it manually.")

# --- Monitoring Table ---
st.markdown("---")
st.subheader("📋 Monitoring")

if os.path.exists(monitored_file):
    render_bill_table(monitored_file)
else:
    st.info("No monitored bills yet. Add bills to monitored_bills.txt to track them here.")

# Committee Hearing Schedules (separate section so it always renders)
st.markdown("---")
st.subheader("📅 Upcoming Committee Hearings")

committees = [
    {"name": "Ethics & Elections", "file": "schedule_ethics_elections.txt"},
    {"name": "House Education Policy", "file": "house_edu_policy.txt"},
    {"name": "House Elementary & Secondary Education Admin", "file": "house_ele_second_admin.txt"},
    {"name": "Senate Education", "file": "senate_education.txt"},
]

for committee in committees:
    if os.path.exists(committee["file"]):
        with open(committee["file"], "r") as f:
            text = f.read().strip()
        if "no hearings scheduled" in text.lower():
            st.markdown(f"**{committee['name']}:** No hearings scheduled")
        else:
            st.markdown(f"**{committee['name']}:** {text}")
    else:
        st.markdown(f"**{committee['name']}:** _No data yet_")
