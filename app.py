import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="ILGA Bill Tracker", layout="wide")

st.title("🏛️ Illinois General Assembly Bill Tracker")

try:
    # 1. Define the files
    time_file = "last_checked.txt"
    data_file = "bills_data.csv"

    # 2. Look at the heartbeat file for the exact run time
    if os.path.exists(time_file):
        timestamp = os.path.getmtime(time_file)
    else:
        # Fallback just in case it hasn't run the new update yet
        timestamp = os.path.getmtime(data_file)

    # 3. Convert the raw server time (UTC) into Central Time
    utc_time = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC"))
    local_time = utc_time.astimezone(ZoneInfo("America/Chicago"))

    # 4. Format it to look nice
    formatted_time = local_time.strftime("%B %d, %Y at %I:%M %p %Z")

    # 5. Display the dynamic "Last Checked" message
    st.markdown(f"**System last checked for updates:** {formatted_time}")

    # 6. Read and display the actual data table
    df = pd.read_csv(data_file)

    # Add "Days Since Last Action" column
    today = datetime.now().date()
    df["Action Date"] = pd.to_datetime(df["Action Date"])
    df["Days Since Action"] = df["Action Date"].apply(
        lambda d: (today - d.date()).days if pd.notna(d) else None
    )
    df["Action Date"] = df["Action Date"].dt.strftime("%Y-%m-%d")

    # Color-code rows by position
    def highlight_position(row):
        position = str(row.get("Position", "")).strip().lower()
        if position == "oppose":
            return ["background-color: #ffcccc"] * len(row)
        elif position == "core bill":
            return ["background-color: #ccffcc"] * len(row)
        elif position == "monitor":
            return ["background-color: #fff3cc"] * len(row)
        return [""] * len(row)

    styled_df = df.style.apply(highlight_position, axis=1)

    st.dataframe(
        styled_df,
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

    # 7. Committee Hearing Schedules
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
            if "No Hearings Scheduled" in text:
                st.markdown(f"**{committee['name']}:** No hearings scheduled")
            else:
                st.markdown(f"**{committee['name']}:** {text}")
        else:
            st.markdown(f"**{committee['name']}:** _No data yet_")

except FileNotFoundError:
    st.markdown("This dashboard tracks target bills and automatically updates daily.")
    st.warning("Data file not found. Wait for the background script to run or trigger it manually.")
