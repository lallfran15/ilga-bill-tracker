import os
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration ---
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

# 1. THE MASTER LIST: Add as many committees here as you want!
COMMITTEES = [
    {
        "name": "Ethics & Elections",
        "url": "https://ilga.gov/House/Committees/Hearings/3110",
        "file": "schedule_ethics_elections.txt"
    },
    {
        "name": "House Education Policy",
        "url": "https://ilga.gov/House/Committees/Hearings/3056", 
        "file": "house_edu_policy.txt"
    },
    {
        "name": "House Elementary & Secondary Education Admin",
        "url": "https://ilga.gov/House/Committees/Hearings/3097",
        "file": "house_ele_second_admin.txt"
    },
    {
        "name": "Senate Education",
        "url": "https://ilga.gov/Senate/Committees/Hearings/3070",
        "file": "senate_education.txt"
    }
]

def send_alert(updates):
    """Sends a single consolidated email for all committee changes."""
    if not EMAIL_USER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("Email credentials missing.")
        return

    subject = f"🏛️ ILGA Hearing Alert: {len(updates)} Committee(s) Updated"
    body = "The following committees have new schedule updates:\n\n"
    
    for update in updates:
        body += f"--- {update['name']} ---\n"
        body += f"{update['text']}\n\n"
        
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
        print("Consolidated email alert sent!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def scrape_all_committees():
    all_updates = []

    # 2. THE LOOP: Go through the list one by one
    for committee in COMMITTEES:
        try:
            response = requests.get(committee["url"])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract the text (adjust this selector if your previous script used a specific HTML tag)
            schedule_text = soup.get_text(separator="\n", strip=True) 
            
            # Load the previous memory for THIS specific committee
            old_text = ""
            if os.path.exists(committee["file"]):
                with open(committee["file"], "r") as f:
                    old_text = f.read()

            # Compare and save if there is a change
            if schedule_text != old_text:
                with open(committee["file"], "w") as f:
                    f.write(schedule_text)
                
                # We only care if a hearing is actually scheduled, not if it just says "No Hearings"
                if "No Hearings Scheduled" not in schedule_text:
                    all_updates.append({
                        "name": committee["name"],
                        "text": schedule_text[:500] # Grabs the first 500 characters of the schedule
                    })
                    
        except Exception as e:
            print(f"Error scraping {committee['name']}: {e}")

    # 3. Send one single email if anything changed
    if all_updates:
        send_alert(all_updates)
    else:
        print("No new hearings scheduled for any tracked committees.")

if __name__ == "__main__":
    scrape_all_committees()
