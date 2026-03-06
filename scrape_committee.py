import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Credentials ---
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER") # Pulls your new GitHub Secret

# --- Committees Configuration ---
# You can add as many committees as you want to this list!
COMMITTEES = [
    {
        "name": "House Ethics and Elections",
        "url": "https://ilga.gov/House/Committees/Hearings/3110",
        "selector": "#scheduled > div > table > tbody > tr > td:nth-child(1)",
        "save_file": "schedule_ethics_elections.txt" # Unique memory file
    },
    {
        "name": "House Education Policy",
        "url": "https://ilga.gov/House/Committees/Hearings/3056",
        "selector": "#scheduled > div > table > tbody > tr > td:nth-child(1)",
        "save_file": "schedule_second_committee.txt" # Unique memory file
    }
]

def send_email_alert(committee_name, committee_url, new_status):
    if not EMAIL_USER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("Missing email credentials. Cannot send alert.")
        return

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_RECEIVER
    msg['Subject'] = f"🚨 ILGA Hearing Alert: {committee_name} Scheduled!"
    
    body = f"The {committee_name} committee has a hearing scheduled!\n\n"
    body += f"HEARING DETAILS:\n{new_status}\n\n"
    body += f"View the committee page here: {committee_url}"
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"[{committee_name}] Email alert sent successfully!")
    except Exception as e:
        print(f"[{committee_name}] Failed to send email: {e}")

def check_schedules():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    # Loop through every committee in your list
    for committee in COMMITTEES:
        print(f"\nChecking schedule for: {committee['name']}...")
        
        # 1. Load yesterday's saved schedule for THIS specific committee
        old_status = ""
        if os.path.exists(committee['save_file']):
            with open(committee['save_file'], "r") as f:
                old_status = f.read().strip()

        # 2. Fetch today's live webpage
        try:
            response = requests.get(committee['url'], headers=headers)
            response.raise_for_status() 
        except requests.exceptions.RequestException as e:
            print(f"[{committee['name']}] Error connecting to ILGA: {e}")
            continue # Skip to the next committee on the list

        # 3. Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 4. Extract the exact text using the selector
        target_element = soup.select_one(committee['selector'])
        
        if not target_element:
            print(f"[{committee['name']}] Error: Could not find the target element.")
            continue
            
        new_status = target_element.get_text(strip=True)

        # 5. Logic: Is it scheduled? AND Is it new?
        is_scheduled = new_status != "No Hearings Scheduled at this time."
        is_new_update = new_status != old_status

        if is_scheduled and is_new_update:
            print(f"[{committee['name']}] New hearing scheduled! Sending email...")
            send_email_alert(committee['name'], committee['url'], new_status)
        elif not is_scheduled:
            print(f"[{committee['name']}] No hearings scheduled today.")
        else:
            print(f"[{committee['name']}] Hearing is scheduled, but you were already alerted.")

        # Always save the newest status so it remembers for tomorrow
        with open(committee['save_file'], "w") as f:
            f.write(new_status)

if __name__ == "__main__":
    check_schedules()
