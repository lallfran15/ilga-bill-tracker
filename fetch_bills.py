import os
import logging
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
import requests

from http_utils import create_session, DEFAULT_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configuration ---
API_KEY = os.environ.get("LEGISCAN_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")
STATE = "IL"
BILLS_FILE = "tracked_bills.txt"
OUTPUT_FILE = "bills_data.csv"
MONITORED_BILLS_FILE = "monitored_bills.txt"
MONITORED_OUTPUT_FILE = "monitored_bills_data.csv"


def send_email_alert(changes):
    if not EMAIL_USER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        logging.info("Email credentials not found. Skipping email alert.")
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
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info("Email alert sent successfully!")
    except Exception as e:
        logging.error("Failed to send email: %s", e)


def detect_changes(master_list, tracked_bills, old_data):
    """Compare fresh API data against old data for tracked bills.

    Returns (results, changes) where results is a list of bill dicts
    and changes is a list of dicts describing what changed.
    """
    results = []
    changes = []

    for key, bill_info in master_list.items():
        if key == "session":
            continue

        bill_number = bill_info.get("number")
        if bill_number in tracked_bills:
            current_action = bill_info.get("last_action")

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
                "Position": tracked_bills[bill_number]["position"],
                "Title": bill_info.get("title"),
                "Last Action": current_action,
                "Action Date": bill_info.get("last_action_date"),
                "Notes": tracked_bills[bill_number]["note"],
                "LegiScan Link": bill_info.get("url")
            })

    return results, changes


def read_bill_list(filepath):
    """Read a bill list file and return a dict of {bill_number: {position, note}}."""
    bills = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split(",", 2)
                    bill_num = parts[0].strip().upper()
                    position = parts[1].strip() if len(parts) > 1 else ""
                    note = parts[2].strip() if len(parts) > 2 else ""
                    bills[bill_num] = {
                        "position": position,
                        "note": note
                    }
    except FileNotFoundError:
        logging.warning("%s not found. Skipping.", filepath)
    return bills


def load_old_data(filepath):
    """Load previous bill data from CSV into a {bill_number: last_action} dict."""
    old_data = {}
    if os.path.exists(filepath):
        try:
            old_df = pd.read_csv(filepath)
            for _, row in old_df.iterrows():
                old_data[row['Bill Number']] = row['Last Action']
        except Exception as e:
            logging.warning("Could not read old data from %s: %s", filepath, e)
    return old_data


def save_results(results, filepath):
    """Save bill results to CSV."""
    if results:
        df = pd.DataFrame(results)
        df.to_csv(filepath, index=False)
        logging.info("Updated %s with %d bills.", filepath, len(results))


def fetch_bill_data():
    if not API_KEY:
        logging.error("LEGISCAN_API_KEY environment variable not found.")
        return

    # 1. Read both bill lists
    tracked_bills = read_bill_list(BILLS_FILE)
    if not tracked_bills:
        logging.error("No tracked bills found in %s.", BILLS_FILE)
        return

    monitored_bills = read_bill_list(MONITORED_BILLS_FILE)

    # 2. Load yesterday's data for comparison
    old_tracked_data = load_old_data(OUTPUT_FILE)
    old_monitored_data = load_old_data(MONITORED_OUTPUT_FILE)

    # 3. Fetch fresh data from LegiScan (single API call for both lists)
    session = create_session()
    url = f"https://api.legiscan.com/?key={API_KEY}&op=getMasterList&state={STATE}"

    try:
        response = session.get(url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logging.error("Failed to fetch data from LegiScan: %s", e)
        return

    if data.get("status") != "OK":
        logging.error("API Error: %s", data.get("alert", "Unknown error"))
        return

    master_list = data.get("masterlist")
    if not master_list:
        logging.error("API returned empty master list.")
        return

    # 4. Process tracked bills (with email alerts)
    results, changes = detect_changes(master_list, tracked_bills, old_tracked_data)
    save_results(results, OUTPUT_FILE)

    if results:
        if changes:
            send_email_alert(changes)
        else:
            logging.info("No status changes detected for tracked bills.")
    else:
        logging.info("No tracked bills found in the current session.")

    # 5. Process monitored bills (no email alerts)
    if monitored_bills:
        monitored_results, _ = detect_changes(master_list, monitored_bills, old_monitored_data)
        save_results(monitored_results, MONITORED_OUTPUT_FILE)

        if not monitored_results:
            logging.info("No monitored bills found in the current session.")
    else:
        logging.info("No monitored bills configured. Skipping.")


if __name__ == "__main__":
    fetch_bill_data()

    # Force a file change so GitHub always records a new timestamp
    with open("last_checked.txt", "w") as f:
        f.write(f"System checked at: {datetime.datetime.now()}")
