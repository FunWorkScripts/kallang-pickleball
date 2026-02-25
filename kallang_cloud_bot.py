"""
The Kallang Pickleball Bot - Cloud Version (Improved)
Better error handling and multiple selector attempts
"""

import os
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
KALLANG_EMAIL = os.getenv('KALLANG_EMAIL')
KALLANG_PASSWORD = os.getenv('KALLANG_PASSWORD')
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')
GMAIL_SENDER = os.getenv('GMAIL_SENDER')
GMAIL_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '300'))

LOGIN_URL = "https://thekallang.perfectgym.com/clientportal2/#/Login"
BOOKING_URL = "https://thekallang.perfectgym.com/clientportal2/#/FacilityBooking?clubId=1&zoneTypeId=42"

def validate_config():
    """Check if all required environment variables are set"""
    required = ['KALLANG_EMAIL', 'KALLANG_PASSWORD', 'NOTIFICATION_EMAIL', 
                'GMAIL_SENDER', 'GMAIL_APP_PASSWORD']
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        logger.error(f"❌ Missing environment variables: {', '.join(missing)}")
        raise ValueError(f"Missing: {missing}")
    
    logger.info("✅ All environment variables configured")

def setup_webdriver():
    """Setup Selenium Chrome WebDriver for cloud environment"""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        logger.info("✅ Chrome WebDriver initialized")
        return driver
    except Exception as e:
        logger.error(f"❌ Failed to initialize WebDriver: {e}")
        raise

def login(driver):
    """Login to The Kallang account with multiple selector attempts"""
    try:
        logger.info("→ Attempting to login...")
        driver.get(LOGIN_URL)
        time.sleep(5)  # Wait longer for page to load
        
        # Try multiple selectors for email field
        email_selectors = [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='text'][placeholder*='email' i]"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.XPATH, "//input[@type='email']"),
            (By.XPATH, "//input[@placeholder[contains(., 'email')]]"),
        ]
        
        email_field = None
        for selector_type, selector_value in email_selectors:
            try:
                logger.info(f"  Trying selector: {selector_value}")
                email_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info(f"  ✅ Found email field!")
                break
            except:
                logger.info(f"  ⚠️  Selector failed, trying next...")
                continue
        
        if not email_field:
            # Try finding by placeholder or label
            try:
                logger.info("  Trying to find email field by all inputs...")
                all_inputs = driver.find_elements(By.TAG_NAME, "input")
                logger.info(f"  Found {len(all_inputs)} input fields")
                for inp in all_inputs:
                    placeholder = inp.get_attribute('placeholder') or ''
                    name = inp.get_attribute('name') or ''
                    input_type = inp.get_attribute('type') or ''
                    logger.info(f"    - Type: {input_type}, Name: {name}, Placeholder: {placeholder}")
                    if 'email' in placeholder.lower() or 'email' in name.lower() or input_type == 'email':
                        email_field = inp
                        logger.info(f"  ✅ Found email field!")
                        break
            except Exception as e:
                logger.error(f"  Error analyzing inputs: {e}")
        
        if not email_field:
            logger.error("❌ Could not find email input field after trying multiple selectors")
            logger.error("Page content preview:")
            logger.error(driver.page_source[:1000])
            return False
        
        email_field.clear()
        email_field.send_keys(KALLANG_EMAIL)
        logger.info(f"✅ Email entered: {KALLANG_EMAIL}")
        time.sleep(1)
        
        # Find password field
        password_selectors = [
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@type='password']"),
        ]
        
        password_field = None
        for selector_type, selector_value in password_selectors:
            try:
                password_field = driver.find_element(selector_type, selector_value)
                break
            except:
                continue
        
        if not password_field:
            logger.error("❌ Could not find password input field")
            return False
        
        password_field.clear()
        password_field.send_keys(KALLANG_PASSWORD)
        logger.info("✅ Password entered")
        time.sleep(1)
        
        # Find and click login button
        login_button_selectors = [
            (By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'Sign In') or contains(text(), 'login')]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
        ]
        
        login_button = None
        for selector_type, selector_value in login_button_selectors:
            try:
                login_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                logger.info(f"✅ Found login button")
                break
            except:
                continue
        
        if not login_button:
            logger.error("❌ Could not find login button")
            return False
        
        login_button.click()
        logger.info("✅ Login button clicked")
        
        # Wait for login to complete
        time.sleep(8)
        
        # Check if login was successful by checking if we're still on login page
        current_url = driver.current_url
        logger.info(f"Current URL after login: {current_url}")
        
        if "login" in current_url.lower():
            logger.warning("⚠️  Still on login page - might still be authenticating")
            time.sleep(3)
        
        logger.info("✅ Login process completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_for_slots(driver):
    """Check if 7-9 PM slots are available for Wed/Fri"""
    try:
        logger.info("→ Checking for available slots...")
        driver.get(BOOKING_URL)
        time.sleep(4)
        
        # Get page source
        page_source = driver.page_source
        
        # Check for 7-9 PM time indicators
        time_patterns = ['19:00', '20:00', '7:00 PM', '8:00 PM', '7:00pm', '8:00pm', '19 ', '20 ']
        has_time_slots = any(pattern in page_source for pattern in time_patterns)
        
        if not has_time_slots:
            logger.info("ℹ No 7-9 PM time slots found on page")
            return False, []
        
        # Find all "Book" buttons
        book_buttons = []
        try:
            buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book')]")
            
            for btn in buttons:
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        parent = btn.find_element(By.XPATH, "..")
                        context = parent.text.lower()
                        
                        if any(pattern in context for pattern in ['19', '20', '7', '8']):
                            book_buttons.append(btn)
                except:
                    pass
        except:
            pass
        
        if book_buttons:
            logger.info(f"🎉 FOUND {len(book_buttons)} AVAILABLE SLOTS FOR 7-9 PM!")
            return True, book_buttons
        else:
            logger.info("ℹ No bookable 7-9 PM slots found")
            return False, []
        
    except Exception as e:
        logger.error(f"❌ Error checking slots: {e}")
        return False, []

def send_notification_email(slot_count):
    """Send email notification that slots were found"""
    try:
        logger.info("→ Sending notification email...")
        
        subject = f"🏓 KALLANG PICKLEBALL - {slot_count} SLOTS FOUND!"
        
        html_body = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background: linear-gradient(135deg, #FF6B9D 0%, #FF8C94 100%); 
                              color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; }}
                    .action {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .button {{ background: #FF6B9D; color: white; padding: 12px 20px; 
                             text-decoration: none; border-radius: 5px; display: inline-block; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🏓 PICKLEBALL SLOTS AVAILABLE!</h1>
                </div>
                <div class="content">
                    <p>Great news! <strong>{slot_count} slot(s)</strong> found for <strong>Wed/Fri 7-9 PM</strong></p>
                    
                    <div class="action">
                        <h3>⚡ QUICK ACTION REQUIRED:</h3>
                        <p>Log in to The Kallang and complete your booking:</p>
                        <a href="https://thekallang.perfectgym.com/clientportal2/#/FacilityBooking?clubId=1&zoneTypeId=42" 
                           class="button">BOOK NOW →</a>
                    </div>
                    
                    <p><strong>⏱️ Time is limited!</strong> Slots disappear fast.</p>
                    <p><em>This alert was sent by your Kallang Pickleball Auto-Bot running on Railway</em></p>
                </div>
            </body>
        </html>
        """
        
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = GMAIL_SENDER
        msg['To'] = NOTIFICATION_EMAIL
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, NOTIFICATION_EMAIL, msg.as_string())
        
        logger.info(f"✅ Email sent to {NOTIFICATION_EMAIL}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

def run_bot():
    """Main bot loop"""
    logger.info("="*70)
    logger.info("🏓 THE KALLANG PICKLEBALL BOT STARTED (IMPROVED VERSION)")
    logger.info("="*70)
    logger.info(f"Configuration:")
    logger.info(f"  Email: {KALLANG_EMAIL}")
    logger.info(f"  Notification: {NOTIFICATION_EMAIL}")
    logger.info(f"  Check interval: {CHECK_INTERVAL} seconds")
    logger.info("="*70)
    
    driver = None
    check_count = 0
    already_notified = False
    
    try:
        validate_config()
        driver = setup_webdriver()
        
        if not login(driver):
            logger.error("❌ Failed to login. Retrying in 30 seconds...")
            time.sleep(30)
            driver.quit()
            # Restart the process
            run_bot()
            return
        
        logger.info("✅ Successfully logged in. Starting monitoring loop...")
        
        while True:
            check_count += 1
            logger.info(f"\n[Check #{check_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            has_slots, buttons = check_for_slots(driver)
            
            if has_slots and not already_notified:
                slot_count = len(buttons)
                send_notification_email(slot_count)
                already_notified = True
                logger.info("✅ Notification sent! Will continue monitoring...")
            
            logger.info(f"Next check in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("\n⏸️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("✅ WebDriver closed")
            except:
                pass

if __name__ == '__main__':
    run_bot()
