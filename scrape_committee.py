import os
import re
import sys
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from http_utils import create_session, DEFAULT_TIMEOUT

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configuration ---
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

DATE_PATTERN = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
MAX_REASONABLE_LENGTH = 5000

# 1. THE MASTER LIST: Add as many committees here as you want!
#    Each committee has a list of selectors tried in order (first match wins).
COMMITTEES = [
    {
        "name": "Ethics & Elections",
        "url": "https://ilga.gov/House/Committees/Hearings/3110",
        "selectors": [
            "#scheduled > div > table > tbody > tr > td:nth-child(1)",
            "#scheduled table td:first-child",
            "#scheduled td",
        ],
        "file": "schedule_ethics_elections.txt"
    },
    {
        "name": "House Education Policy",
        "url": "https://ilga.gov/House/Committees/Hearings/3056",
        "selectors": [
            "#scheduled > div > table > tbody > tr > td:nth-child(1)",
            "#scheduled table td:first-child",
            "#scheduled td",
        ],
        "file": "house_edu_policy.txt"
    },
    {
        "name": "House Elementary & Secondary Education Admin",
        "url": "https://ilga.gov/House/Committees/Hearings/3097",
        "selectors": [
            "#scheduled > div > table > tbody > tr > td:nth-child(1)",
            "#scheduled table td:first-child",
            "#scheduled td",
        ],
        "file": "house_ele_second_admin.txt"
    },
    {
        "name": "Senate Education",
        "url": "https://ilga.gov/Senate/Committees/Hearings/3070",
        "selectors": [
            "#scheduled > div > table > tbody > tr > td > p",
            "#scheduled > div > table > tbody > tr > td:nth-child(1)",
            "#scheduled table td:first-child",
            "#scheduled td",
        ],
        "file": "senate_education.txt"
    }
]


def extract_schedule_text(html_content, selectors):
    """Extract schedule text from HTML using a list of fallback selectors.

    Returns the extracted text, or None if no selector matched.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(separator="\n", strip=True)
            if text:
                return text
    return None


def validate_schedule_text(text, committee_name):
    """Check that extracted text looks plausible. Returns True if valid."""
    if not text or not text.strip():
        logging.warning("%s: Extracted text is empty.", committee_name)
        return False
    if len(text) > MAX_REASONABLE_LENGTH:
        logging.warning(
            "%s: Extracted text is suspiciously long (%d chars) — selector may be too broad.",
            committee_name, len(text),
        )
        return False
    if not DATE_PATTERN.search(text) and "no hearings scheduled" not in text.lower():
        logging.warning(
            "%s: Extracted text has no date pattern and no 'No Hearings Scheduled' — may be wrong content.",
            committee_name,
        )
    return True


def has_schedule_changed(new_text, old_text):
    """Compare schedule texts with whitespace normalization."""
    return new_text.strip() != old_text.strip()


def send_alert(updates, failures=None):
    """Sends a single consolidated email for all committee changes and failures."""
    if not EMAIL_USER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        logging.info("Email credentials missing. Skipping alert.")
        return

    subject = f"🏛️ ILGA Hearing Alert: {len(updates)} Committee(s) Updated"
    body = ""

    if failures:
        body += "⚠️ SCRAPER WARNINGS:\n"
        for name in failures:
            body += f"  - {name}: Could not extract data (selectors may need updating)\n"
        body += "\n"

    if updates:
        body += "The following committees have new schedule updates:\n\n"
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
        logging.info("Email alert sent.")
    except Exception as e:
        logging.error("Failed to send email: %s", e)


def scrape_all_committees():
    all_updates = []
    failures = []
    successes = 0

    session = create_session()

    for committee in COMMITTEES:
        try:
            response = session.get(committee["url"], timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()

            schedule_text = extract_schedule_text(response.content, committee["selectors"])

            if schedule_text is None:
                logging.warning(
                    "Could not find any matching selector on the %s page.", committee["name"]
                )
                failures.append(committee["name"])
                continue

            if not validate_schedule_text(schedule_text, committee["name"]):
                failures.append(committee["name"])
                continue

            successes += 1

            # Load the previous data for this committee
            old_text = ""
            if os.path.exists(committee["file"]):
                with open(committee["file"], "r") as f:
                    old_text = f.read()

            # Compare and save if there is a change
            if has_schedule_changed(schedule_text, old_text):
                with open(committee["file"], "w") as f:
                    f.write(schedule_text)

                # We only care if a hearing is actually scheduled
                if "no hearings scheduled" not in schedule_text.lower():
                    all_updates.append({
                        "name": committee["name"],
                        "text": schedule_text[:500]
                    })

        except Exception as e:
            logging.error("Error scraping %s: %s", committee["name"], e, exc_info=True)
            failures.append(committee["name"])

    # Send one single email if anything changed or failed
    if all_updates or failures:
        send_alert(all_updates, failures)
    else:
        logging.info("No new hearings scheduled for any tracked committees.")

    total = len(COMMITTEES)
    logging.info(
        "Scrape complete. %d/%d succeeded, %d failed, %d alert(s).",
        successes, total, len(failures), len(all_updates),
    )

    # Exit with error if ALL committees failed
    if successes == 0 and total > 0:
        logging.error("All committees failed to scrape. Exiting with error.")
        sys.exit(1)


if __name__ == "__main__":
    scrape_all_committees()
