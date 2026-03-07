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
