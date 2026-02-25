"""
The Kallang Pickleball Bot - Cloud Version (Enhanced Logging)
Shows exactly what facility and times are being checked
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
    """Login to The Kallang account"""
    try:
        logger.info("→ Attempting to login...")
        driver.get(LOGIN_URL)
        time.sleep(5)
        
        # Find email field
        email_field = None
        email_selectors = [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[type='text'][placeholder*='email' i]"),
            (By.CSS_SELECTOR, "input[name='email']"),
        ]
        
        for selector_type, selector_value in email_selectors:
            try:
                email_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                logger.info("✅ Found email field!")
                break
            except:
                continue
        
        if not email_field:
            logger.error("❌ Could not find email input field")
            return False
        
        email_field.clear()
        email_field.send_keys(KALLANG_EMAIL)
        logger.info(f"✅ Email entered: {KALLANG_EMAIL}")
        time.sleep(2)
        
        # Find password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(KALLANG_PASSWORD)
        logger.info("✅ Password entered")
        time.sleep(2)
        
        # Try to find and click login button
        logger.info("→ Looking for login button...")
        
        button_found = False
        button_selectors = [
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Sign In')]"),
            (By.XPATH, "//button[@type='submit']"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH, "//button"),
        ]
        
        for selector_type, selector_value in button_selectors:
            try:
                button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                logger.info(f"✅ Found and clicked button")
                button.click()
                button_found = True
                break
            except:
                continue
        
        # If button not found, use JavaScript
        if not button_found:
            logger.info("→ Using JavaScript to click button...")
            try:
                driver.execute_script("""
                    var buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        if (btn.textContent.toLowerCase().includes('login') || 
                            btn.textContent.toLowerCase().includes('sign in') ||
                            btn.type === 'submit') {
                            btn.click();
                            break;
                        }
                    }
                """)
                logger.info("✅ Clicked button via JavaScript")
                button_found = True
            except Exception as e:
                logger.error(f"❌ JavaScript click failed: {e}")
        
        if not button_found:
            logger.info("→ Trying to press Enter key...")
            try:
                password_field.send_keys("\n")
                logger.info("✅ Pressed Enter")
            except:
                logger.error("❌ Failed to press Enter")
                return False
        
        time.sleep(8)
        logger.info("✅ Login process completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_for_slots(driver):
    """Check if 7-9 PM slots are available for Wed/Fri with detailed logging"""
    try:
        logger.info("→ Checking for available slots...")
        driver.get(BOOKING_URL)
        time.sleep(4)
        
        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Log what facility we're on
        logger.info("📍 Current page analysis:")
        
        # Check for pickleball court reference
        if "pickleball" in page_source.lower():
            logger.info("✅ Pickleball court page detected")
        else:
            logger.warning("⚠️ Pickleball mention not found - checking anyway")
        
        # Check for dates (Wed/Fri)
        if "WEDNESDAY" in page_text or "Wednesday" in page_text or "WED" in page_text:
            logger.info("✅ Wednesday found on page")
        if "FRIDAY" in page_text or "Friday" in page_text or "FRI" in page_text:
            logger.info("✅ Friday found on page")
        
        # Check for 7-9 PM time indicators
        time_patterns = {
            '19:00': '7 PM',
            '20:00': '8 PM',
            '7:00 PM': '7 PM (format 1)',
            '8:00 PM': '8 PM (format 1)',
            '7:00pm': '7 PM (format 2)',
            '8:00pm': '8 PM (format 2)',
        }
        
        found_times = []
        for pattern, description in time_patterns.items():
            if pattern in page_source:
                found_times.append(f"{description} ({pattern})")
                logger.info(f"  ✅ Found: {description}")
        
        if not found_times:
            logger.info("ℹ No 7-9 PM time slots (19:00-20:00) found on page")
            logger.info("📊 Sample of page content (first 500 chars):")
            logger.info(page_text[:500])
            return False, []
        
        logger.info(f"✅ Found {len(found_times)} time pattern(s)")
        
        # Find all "Book" buttons with detailed info
        book_buttons = []
        try:
            buttons = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'book')]")
            logger.info(f"📊 Found {len(buttons)} 'Book' buttons on page")
            
            for idx, btn in enumerate(buttons, 1):
                try:
                    if btn.is_displayed() and btn.is_enabled():
                        parent = btn.find_element(By.XPATH, "..")
                        context = parent.text.lower()
                        button_text = btn.text
                        
                        logger.info(f"  Button #{idx}: '{button_text}' | Context: {context[:80]}...")
                        
                        # Check for 7-9 PM context
                        if any(pattern in context for pattern in ['19', '20', '7', '8']):
                            book_buttons.append(btn)
                            logger.info(f"    ✅ Matches 7-9 PM criteria")
                        else:
                            logger.info(f"    ⚠️ Doesn't match 7-9 PM criteria")
                except Exception as e:
                    logger.info(f"  Button #{idx}: Error processing - {e}")
                    
        except Exception as e:
            logger.error(f"Error finding buttons: {e}")
        
        if book_buttons:
            logger.info(f"🎉 FOUND {len(book_buttons)} AVAILABLE SLOTS FOR 7-9 PM!")
            return True, book_buttons
        else:
            logger.info("ℹ No bookable 7-9 PM slots matching criteria found")
            return False, []
        
    except Exception as e:
        logger.error(f"❌ Error checking slots: {e}")
        import traceback
        logger.error(traceback.format_exc())
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
        
        logger.info(f"✅ Email sent to {NOTIFICATION_EMAIL}!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

def run_bot():
    """Main bot loop"""
    logger.info("="*70)
    logger.info("🏓 THE KALLANG PICKLEBALL BOT STARTED (ENHANCED LOGGING)")
    logger.info("="*70)
    logger.info(f"Configuration:")
    logger.info(f"  Email: {KALLANG_EMAIL}")
    logger.info(f"  Notification: {NOTIFICATION_EMAIL}")
    logger.info(f"  Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
    logger.info(f"  Looking for: Pickleball Courts, Wed/Fri, 7-9 PM (19:00-20:00)")
    logger.info("="*70)
    
    driver = None
    check_count = 0
    already_notified = False
    
    try:
        validate_config()
        driver = setup_webdriver()
        
        if not login(driver):
            logger.error("❌ Failed to login. Retrying...")
            time.sleep(30)
            driver.quit()
            run_bot()
            return
        
        logger.info("✅ Successfully logged in. Starting monitoring loop...")
        
        while True:
            check_count += 1
            logger.info(f"\n{'='*70}")
            logger.info(f"[Check #{check_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*70}")
            
            has_slots, buttons = check_for_slots(driver)
            
            if has_slots and not already_notified:
                slot_count = len(buttons)
                logger.info(f"\n🔔 SLOTS DETECTED! Sending notification...")
                send_notification_email(slot_count)
                already_notified = True
                logger.info("✅ Notification email sent! Continuing to monitor...")
            
            logger.info(f"\n⏰ Next check in {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
            logger.info(f"Next check at: {datetime.fromtimestamp(time.time() + CHECK_INTERVAL).strftime('%Y-%m-%d %H:%M:%S')}")
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
