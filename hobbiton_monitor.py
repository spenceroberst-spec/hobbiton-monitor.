#!/usr/bin/env python3
"""
Hobbiton Tours Availability Monitor
Checks for tour availability on February 13 and 16, 2026 for 2 people
Sends email notification when tickets become available
"""

import time
import smtplib
import logging
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import os  # Added for environment variables

# --- Configuration ---
TARGET_DATES = ["13/02/2026", "16/02/2026"]  # DD/MM/YYYY format for the website
NUM_PEOPLE = 2
CHECK_INTERVAL_SECONDS = 30 * 60  # Check every 30 minutes
TOUR_URL = "https://www.hobbitontours.com/experiences/hobbiton-movie-set-tour/"

# --- Email Configuration ---
# STARTUP: Email config is now pulled from environment variables for privacy
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO")

# Fallback for local testing if env vars aren't set (warn user if missing)
if not EMAIL_FROM:
    logging.warning("EMAIL_FROM not set in environment variables. Emailing will fail.")
if not EMAIL_TO:
     # Default to sending to self if TO is not set
    EMAIL_TO = EMAIL_FROM

# STARTUP: We check for the password in the environment variables (for GitHub Actions)
# faster and safer than hardcoding it.
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") 
if not EMAIL_PASSWORD:
    # Only use this fallback if you possess the file locally and know it's safe
    # But since we are going public, we remove the hardcoded password entirely or make it blank.
    EMAIL_PASSWORD = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hobbiton_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def send_email_notification(subject, message):
    """Send email notification when availability is found"""
    if "YOUR_APP_PASSWORD" in EMAIL_PASSWORD:
        logging.error("Cannot send email: Email password not configured.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        server.quit()

        logging.info(f"Email notification sent successfully to {EMAIL_TO}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False

def check_availability(target_date_str):
    """Check Hobbiton Tours website for availability"""
    # Create log format YYYY-MM-DD
    parts = target_date_str.split('/')
    target_date_log = f"{parts[2]}-{parts[1]}-{parts[0]}"

    driver = None
    try:
        # 1. Setup Driver
        options = webdriver.ChromeOptions()
        # Keep headless option for background running, but useful to comment out for debug
        options.add_argument('--headless') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # 2. Navigate to Tour Page
        logging.info(f"Navigating to {TOUR_URL}")
        driver.get(TOUR_URL)
        
        wait = WebDriverWait(driver, 20)
        
        # 3. Handle Cookie Consent (Critical for visibility)
        try:
            # Selector found from debug: .js-confirm__yes
            cookie_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".js-confirm__yes")))
            cookie_btn.click()
            logging.info("Accepted cookies")
            time.sleep(1) # Wait for banner to disappear
        except:
            logging.info("No cookie banner found or already accepted")

        # 4. Scroll to Booking Form
        # The form is down the page, we need to scroll to ensure elements are interactive/visible
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)

        # 5. Fill Booking Form
        logging.info(f"Attempting to select date: {target_date_str}")
        
        # Use Javascript to set the date directly
        # Debugging showed the input has class 'js-datepicker'
        js_set_date = f"""
        var dateInput = document.querySelector('.js-datepicker');
        if (dateInput) {{
            dateInput.value = '{target_date_str}';
            dateInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
            dateInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
            return true;
        }}
        return false;
        """
        success = driver.execute_script(js_set_date)
        
        if not success:
            logging.error("Could not find date picker element via JS")
            driver.save_screenshot('debug_failed_datepicker.png')
            return None
            
        time.sleep(1) 
        
        # 6. Click "Check Availability"
        # Debugging showed multiple buttons, we need the visible one in the booking bar
        # Selector: .c-hero__booking button.js-tour__book-button
        try:
            check_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".c-hero__booking button.js-tour__book-button")))
            
            # Ensure it's not covered by the sticky header by scrolling it safely into center view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", check_btn)
            time.sleep(0.5)
            
            # Click via JS to be safe against overlays
            driver.execute_script("arguments[0].click();", check_btn)
            logging.info("Clicked Check Availability button")
        except TimeoutException:
            logging.error("Could not find Check Availability button")
            driver.save_screenshot('debug_no_button.png')
            return None
        
        # 7. Wait for Results
        time.sleep(5) 
        
        page_source = driver.page_source.lower()
        
        # Analyze results
        # "Sold Out" status is indicated by elements with "Fully Booked" text
        # The browser subagent found: <div class="standard-fee unavailable">...Fully Booked...</div>
        
        if "fully booked" in page_source or "no availability" in page_source:
             logging.info(f"Status: SOLD OUT for {target_date_log} (Confirmed 'Fully Booked')")
             # Take a screenshot to prove it
             driver.save_screenshot('debug_sold_out.png')
             return False
        
        # Positive indicators
        # If we see "Select" or "Book" buttons that are NOT disabled/unavailable
        if "select" in page_source or "book now" in page_source:
             # Double check we aren't just seeing the header button
             # Look for specific time slots
             if "time-slot" in page_source or "available" in page_source:
                 logging.info("Status: POTENTIAL AVAILABILITY FOUND!")
                 return True
             
        # Fallback check
        if "we do not have any tours available" in page_source:
             logging.info(f"Status: SOLD OUT for {target_date_log} (No tours message)")
             return False

        logging.warning("Status: Unsure. Page content ambiguous. Check 'debug_last_check.png'.")
        driver.save_screenshot('debug_last_check.png')
        return None

    except Exception as e:
        logging.error(f"Error during check: {str(e)}")
        if driver:
            try:
                driver.save_screenshot('debug_error.png')
            except:
                pass
        return None
    finally:
        if driver:
            driver.quit()

def main():
    logging.info("="*60)
    logging.info("Hobbiton Monitor v2.0 Started")
    logging.info(f"Checking {TOUR_URL}")
    logging.info(f"Dates: {TARGET_DATES}")
    logging.info(f"Email Configured: {'Yes' if 'YOUR_APP_PASSWORD' not in EMAIL_PASSWORD else 'NO (Please set password)'}")
    logging.info("="*60)
    
    # Run once immediately
    for date_str in TARGET_DATES:
        check_availability(date_str)
    
    # Loop
    while True:
        # If running in GitHub Actions (or specified), we might only want to run once
        # But actually, the best way for GitHub Actions is to just run check_availability() once and exit.
        # We can detect this with an environment variable.
        if os.environ.get("GITHUB_ACTIONS") == "true":
            logging.info("Running in GitHub Actions - executing single check and exiting.")
            return

        logging.info(f"Sleeping for {CHECK_INTERVAL_SECONDS} seconds...")
        time.sleep(CHECK_INTERVAL_SECONDS)
        
        for date_str in TARGET_DATES:
            is_available = check_availability(date_str)
            
            if is_available:
                send_email_notification(
                    "🎉 HOBBITON ALERT: Tickets Available!",
                    f"Found availability for {date_str}!\nCheck immediately: {TOUR_URL}"
                )

if __name__ == "__main__":
    main()
