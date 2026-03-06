import streamlit as st
import pandas as pd
import os
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="ILGA Bill Tracker", layout="wide")

st.title("🏛️ Illinois General Assembly Bill Tracker")

try:
    # 1. Look at the data file and get the exact time it was saved
    file_path = "bills_data.csv"
    timestamp = os.path.getmtime(file_path)
    
    # 2. Convert the raw server time (UTC) into Central Time
    utc_time = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC"))
    local_time = utc_time.astimezone(ZoneInfo("America/Chicago"))
    
    # 3. Format it to look nice (e.g., "March 05, 2026 at 08:02 AM CST")
    formatted_time = local_time.strftime("%B %d, %Y at %I:%M %p %Z")
    
    # 4. Display the dynamic message
    st.markdown(f"**This dashboard was last updated:** {formatted_time}")

    # 5. Read and display the data table
    df = pd.read_csv(file_path)
    
    st.dataframe(
        df,
        column_config={
            "LegiScan Link": st.column_config.LinkColumn("View on LegiScan")
        },
        hide_index=True,
        use_container_width=True
    )
    
except FileNotFoundError:
    st.markdown("This dashboard tracks target bills and automatically updates daily.")
    st.warning("Data file not found. Wait for the background script to run or trigger it manually.")
