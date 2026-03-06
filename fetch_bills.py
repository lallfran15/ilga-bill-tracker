import os
import requests
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
API_KEY = os.environ.get("LEGISCAN_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
#EMAIL_RECEIVER = EMAIL_USER # Sends the alert directly to yourself
STATE = "IL"
BILLS_FILE = "tracked_bills.txt"
OUTPUT_FILE = "bills_data.csv"

def send_email_alert(changes):
    """Logs into the SMTP server and sends a summary of bill changes."""
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("Email credentials not found. Skipping email alert.")
        return

    subject = f"🏛️ ILGA Bill Tracker: {len(changes)} Update(s)"
    body = "The following bills have updated statuses:\n\n"
    for change in changes:
        body += f"• {change['bill']}: '{change['old']}' ➡️ '{change['new']}'\n"
    body += "\nCheck your Streamlit dashboard for full details."

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Gmail SMTP Configuration
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email alert sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Failed to send email: Authentication failed. If using Gmail, ensure you are using an App Password instead of your regular password.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def fetch_bill_data():
    if not API_KEY:
        print("Error: LEGISCAN_API_KEY environment variable not found.")
        return

    # 1. Read tracked bills
    try:
        with open(BILLS_FILE, "r") as f:
            tracked_bills = [line.strip().upper() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print(f"Error: {BILLS_FILE} not found.")
        return

    # 2. Load yesterday's data into memory to compare
    old_data = {}
    if os.path.exists(OUTPUT_FILE):
        try:
            old_df = pd.read_csv(OUTPUT_FILE)
            for _, row in old_df.iterrows():
                old_data[row['Bill Number']] = row['Last Action']
        except Exception as e:
            print(f"Could not read old data: {e}")

    # 3. Fetch fresh data from LegiScan
    url = f"https://api.legiscan.com/?key={API_KEY}&op=getMasterList&state={STATE}"
    response = requests.get(url)
    data = response.json()

    if data.get("status") != "OK":
        print(f"API Error: {data.get('alert', 'Unknown error')}")
        return

    master_list = data["masterlist"]
    results = []
    changes = []

    # 4. Filter and look for changes
    for key, bill_info in master_list.items():
        if key == "session": 
            continue 
            
        bill_number = bill_info.get("number")
        if bill_number in tracked_bills:
            current_action = bill_info.get("last_action")
            
            # Check if this bill existed yesterday and if the status changed
            if bill_number in old_data:
                previous_action = old_data[bill_number]
                if current_action != previous_action:
                    changes.append({
                        'bill': bill_number,
                        'old': previous_action,
                        'new': current_action
                    })
            
            results.append({
                "Bill Number": bill_number,
                "Title": bill_info.get("title"),
                "Last Action": current_action,
                "Action Date": bill_info.get("last_action_date"),
                "LegiScan Link": bill_info.get("url")
            })

    # 5. Save the new data, overwriting yesterday's file
    if results:
        df = pd.DataFrame(results)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"Success! Updated {OUTPUT_FILE} with {len(results)} bills.")
        
        # 6. Trigger the email if the changes list isn't empty
        if changes:
            send_email_alert(changes)
        else:
            print("No status changes detected today.")
    else:
        print("No tracked bills found in the current session.")

if __name__ == "__main__":
    fetch_bill_data()
