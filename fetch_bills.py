import os
import requests
import pandas as pd

# Configuration
API_KEY = os.environ.get("LEGISCAN_API_KEY")
STATE = "IL"
BILLS_FILE = "tracked_bills.txt"
OUTPUT_FILE = "bills_data.csv"

def fetch_bill_data():
    if not API_KEY:
        print("Error: LEGISCAN_API_KEY environment variable not found.")
        return

    # 1. Read the list of bills you care about
    try:
        with open(BILLS_FILE, "r") as f:
            tracked_bills = [line.strip().upper() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"Error: {BILLS_FILE} not found.")
        return

    # 2. Fetch the entire active session master list for Illinois (1 API Call)
    url = f"https://api.legiscan.com/?key={API_KEY}&op=getMasterList&state={STATE}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        print(f"API Error: {data.get('alert', 'Unknown error')}")
        return

    master_list = data["masterlist"]
    results = []

    # 3. Filter the master list for your specific tracked bills
    for key, bill_info in master_list.items():
        if key == "session": 
            continue # Skip the session metadata node
            
        bill_number = bill_info.get("number")
        if bill_number in tracked_bills:
            results.append({
                "Bill Number": bill_number,
                "Title": bill_info.get("title"),
                "Last Action": bill_info.get("last_action"),
                "Action Date": bill_info.get("last_action_date"),
                "LegiScan Link": bill_info.get("url")
            })

    # 4. Save the results to a CSV for Streamlit to read
    if results:
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Success! Updated {OUTPUT_FILE} with {len(results)} bills.")
    else:
        print("No tracked bills found in the current session.")

if __name__ == "__main__":
    fetch_bill_data()
