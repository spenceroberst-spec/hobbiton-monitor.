# Hobbiton Tours Availability Monitor

Automatically monitors the Hobbiton Tours website for ticket availability on February 16, 2025 for 2 people and sends email notifications when tickets become available.

## Features

- Checks availability every 30 minutes
- Sends email notifications when tickets are found
- Runs in headless mode (no browser window)
- Logs all activity to file and console
- Takes screenshots for debugging

## Setup Instructions

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Chrome WebDriver

The script uses Selenium with Chrome. Make sure you have Chrome installed, then install chromedriver:

**On macOS:**
```bash
brew install chromedriver
```

**On Linux:**
```bash
sudo apt-get install chromium-chromedriver
```

**On Windows:**
Download from https://chromedriver.chromium.org/ and add to PATH

### 3. Configure Email Settings

Edit the email configuration section in `hobbiton_monitor.py` (lines 20-25):

```python
EMAIL_FROM = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"
EMAIL_TO = "recipient@example.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
```

#### Gmail Setup:
1. Enable 2-factor authentication on your Google account
2. Generate an app-specific password at https://myaccount.google.com/apppasswords
3. Use the app password (not your regular password) in the script

#### Other Email Providers:
- **Outlook**: smtp-mail.outlook.com, port 587
- **Yahoo**: smtp.mail.yahoo.com, port 587
- Check your provider's SMTP settings

### 4. Run the Monitor

```bash
python3 hobbiton_monitor.py
```

The script will:
- Start monitoring immediately
- Send a startup confirmation email
- Check every 30 minutes
- Log activity to `hobbiton_monitor.log`
- Send an email when availability is found

### 5. Stop the Monitor

Press `Ctrl+C` to stop the script. It will send a shutdown notification email.

## Running in the Background

### On macOS/Linux:

```bash
# Run in background
nohup python3 hobbiton_monitor.py &

# Check if running
ps aux | grep hobbiton_monitor

# Stop the process
kill <process_id>
```

### Using screen (recommended for remote servers):

```bash
# Start a screen session
screen -S hobbiton

# Run the script
python3 hobbiton_monitor.py

# Detach: Press Ctrl+A, then D
# Reattach: screen -r hobbiton
# Kill session: screen -X -S hobbiton quit
```

## Customization

Edit these variables in `hobbiton_monitor.py`:

```python
TARGET_DATE = "2025-02-16"  # Change date
NUM_PEOPLE = 2              # Change party size
CHECK_INTERVAL = 30 * 60    # Change check frequency (in seconds)
```

## Troubleshooting

### "Message: 'chromedriver' executable needs to be in PATH"
- Install chromedriver (see setup instructions above)

### Email not sending
- Check your email credentials
- For Gmail, ensure you're using an app password
- Check that 2FA is enabled for Gmail
- Try a test email separately to verify SMTP settings

### Script can't find availability
- Check `hobbiton_page.png` screenshot to see what the page looks like
- The website structure may have changed - you may need to update the selectors
- Check `hobbiton_monitor.log` for detailed error messages

## Notes

- The script takes a screenshot (`hobbiton_page.png`) on each check for debugging
- All activity is logged to `hobbiton_monitor.log`
- The script will continue running until manually stopped
- Make sure your computer stays on and connected to the internet

## Important

Hobbiton Tours' website structure may change over time. If the script stops working:

1. Check the log file for errors
2. Examine the screenshot to see the current page structure
3. You may need to update the web scraping logic to match the current website

This is a basic monitoring script. For production use, consider:
- Adding more robust error handling
- Implementing proxy rotation if making frequent requests
- Respecting the website's robots.txt and terms of service
- Using official APIs if available
