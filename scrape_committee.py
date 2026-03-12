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
        "selector": "#scheduled > div > table > tbody > tr > td:nth-child(1)",
        "file": "schedule_ethics_elections.txt"
    },
    {
        "name": "House Education Policy",
        "url": "https://ilga.gov/House/Committees/Hearings/3056",
        "selector": "#scheduled > div > table > tbody > tr > td:nth-child(1)",
        "file": "house_edu_policy.txt"
    },
    {
        "name": "House Elementary & Secondary Education Admin",
        "url": "https://ilga.gov/House/Committees/Hearings/3097",
        "selector": "#scheduled > div > table > tbody > tr > td:nth-child(1)",
        "file": "house_ele_second_admin.txt"
    },
    {
        "name": "Senate Education",
        "url": "https://ilga.gov/Senate/Committees/Hearings/3070",
        "selector": "#scheduled > div > table > tbody > tr > td > p",
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

    for committee in COMMITTEES:
        try:
            response = requests.get(committee["url"])
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 2. THE PRECISION EXTRACTION: Only grab the specific HTML element
            target_element = soup.select_one(committee["selector"])
            
            if target_element:
                schedule_text = target_element.get_text(separator="\n", strip=True) 
            else:
                print(f"Warning: Could not find the HTML selector '{committee['selector']}' on the {committee['name']} page.")
                continue # Skip this committee and move to the next one
            
            # Load the previous memory for THIS specific committee
            old_text = ""
            if os.path.exists(committee["file"]):
                with open(committee["file"], "r") as f:
                    old_text = f.read()

            # Compare and save if there is a change
            if schedule_text != old_text:
                with open(committee["file"], "w") as f:
                    f.write(schedule_text)
                
                # We only care if a hearing is actually scheduled
                if "No Hearings Scheduled" not in schedule_text:
                    all_updates.append({
                        "name": committee["name"],
                        "text": schedule_text[:500] 
                    })
                    
        except Exception as e:
            print(f"Error scraping {committee['name']}: {e}")

    # Send one single email if anything changed
    if all_updates:
        send_alert(all_updates)
    else:
        print("No new hearings scheduled for any tracked committees.")

if __name__ == "__main__":
    scrape_all_committees()
