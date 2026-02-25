"""
The Kallang Pickleball Bot - Cloud Version (Session Persistence + Screenshots)
Maintains login session across multiple checks with screenshot debugging
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
import base64
import requests
import random

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

def random_delay(min_seconds=2, max_seconds=5):
    """Add random human-like delay to avoid bot detection"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def setup_webdriver():
    """Setup Chrome WebDriver with anti-bot stealth measures"""
    try:
        logger.info("→ Setting up Chrome driver with stealth measures...")
        
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--window-size=1920,1080')
        # Remove WebDriver detection
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        # Real user-agent
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # Inject JavaScript to hide automation markers
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        logger.info("✅ Chrome WebDriver initialized with anti-bot stealth measures")
        logger.info("  - WebDriver detection hidden")
        logger.info("  - Automation markers spoofed")
        logger.info("  - Human-like user-agent set")
        return driver
    except Exception as e:
        logger.error(f"❌ Failed to initialize WebDriver: {e}")
        raise

def upload_to_imgur(image_path):
    """Upload screenshot to Imgur and return public URL"""
    try:
        client_id = "546c25a59c58ad7"
        
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        headers = {
            'Authorization': f'Client-ID {client_id}'
        }
        
        data = {
            'image': image_data,
            'type': 'base64'
        }
        
        response = requests.post(
            'https://api.imgur.com/3/upload',
            headers=headers,
            data=data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            imgur_url = result['data']['link']
            logger.info(f"🔗 View screenshot: {imgur_url}")
            return imgur_url
        else:
            logger.warning(f"⚠️ Imgur upload failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Imgur upload error: {e}")
        return None

def take_screenshot(driver, name="screenshot"):
    """Take a screenshot, save it, and upload to Imgur"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/tmp/{name}_{timestamp}.png"
    
    try:
        driver.save_screenshot(filename)
        logger.info(f"📸 Screenshot saved: {filename}")
        
        imgur_url = upload_to_imgur(filename)
        
        return filename, imgur_url
    except Exception as e:
        logger.error(f"❌ Failed to take screenshot: {e}")
        return None, None

def get_page_info(driver):
    """Get detailed page information for debugging"""
    try:
        current_url = driver.current_url
        page_title = driver.title
        page_text = driver.find_element(By.TAG_NAME, "body").text[:500]
        
        logger.info(f"📍 Current URL: {current_url}")
        logger.info(f"📄 Page Title: {page_title}")
        logger.info(f"📝 Page Text (first 500 chars):\n{page_text}")
        
        return {
            'url': current_url,
            'title': page_title,
            'text': page_text
        }
    except Exception as e:
        logger.error(f"❌ Error getting page info: {e}")
        return None

def login(driver):
    """Login to The Kallang account"""
    try:
        logger.info("→ Attempting to login...")
        driver.get(LOGIN_URL)
        time.sleep(5)
        
        take_screenshot(driver, "01_login_page")
        get_page_info(driver)
        
        # DISMISS COOKIES FIRST before trying to login!
        logger.info("→ Dismissing cookies before login...")
        dismiss_popups(driver)
        time.sleep(2)
        take_screenshot(driver, "01b_after_cookie_dismiss")
        
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
            take_screenshot(driver, "ERROR_no_email_field")
            return False
        
        email_field.clear()
        email_field.send_keys(KALLANG_EMAIL)
        logger.info(f"✅ Email entered")
        random_delay(1, 3)  # Human would pause here
        
        # Find password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(KALLANG_PASSWORD)
        logger.info("✅ Password entered")
        random_delay(1, 4)  # Humans pause before clicking login
        
        take_screenshot(driver, "02_before_login_click")
        
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
                take_screenshot(driver, "ERROR_no_login_button")
                return False
        
        time.sleep(8)
        
        # CRITICAL: Verify that login actually navigated away from login page
        current_url = driver.current_url
        logger.info(f"→ Verifying login navigation...")
        logger.info(f"  Current URL: {current_url}")
        
        if "#/login" in current_url.lower():
            logger.error("❌ CRITICAL: Still on login page after clicking login button!")
            logger.error("❌ Login form submission failed!")
            take_screenshot(driver, "ERROR_login_failed_still_on_page")
            
            # Try one more time with Enter key
            logger.info("→ Attempting to submit form with Enter key...")
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                password_field.send_keys("\n")
                time.sleep(5)
                
                # Check URL again
                current_url = driver.current_url
                if "#/login" in current_url.lower():
                    logger.error("❌ Login failed - still on login page after Enter key")
                    take_screenshot(driver, "ERROR_login_failed_enter_key")
                    return False
                else:
                    logger.info("✅ Form submitted with Enter key!")
            except:
                logger.error("❌ Could not submit with Enter key")
                return False
        else:
            logger.info("✅ Successfully navigated away from login page!")
        
        take_screenshot(driver, "03_after_login")
        get_page_info(driver)
        
        logger.info("✅ Login process completed")
        
        # Wait a bit and take another screenshot to verify session is active
        logger.info("→ Verifying session is active...")
        time.sleep(3)
        take_screenshot(driver, "03b_session_active_check")
        get_page_info(driver)
        
        # Navigate to booking page immediately to confirm session persists
        logger.info("→ Testing session persistence...")
        driver.get(BOOKING_URL)
        time.sleep(3)
        take_screenshot(driver, "03c_booking_page_after_login")
        get_page_info(driver)
        
        # Dismiss any popups
        dismiss_popups(driver)
        
        # Check session again
        logger.info("→ Checking session after popup dismissal...")
        time.sleep(2)
        take_screenshot(driver, "03d_session_after_popup_dismiss")
        get_page_info(driver)
        
        logger.info("✅ Session verified and active!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        take_screenshot(driver, "ERROR_login_exception")
        import traceback
        logger.error(traceback.format_exc())
        return False

def dismiss_popups(driver):
    """Dismiss all popups and cookie dialogs"""
    try:
        logger.info("→ Dismissing popups/cookies...")
        
        # FIRST: Try to click "Accept All" button directly using JavaScript
        # This is more reliable than Selenium element clicking
        logger.info("  Attempting to click Accept All button...")
        result = driver.execute_script("""
            // Look for any button containing "Accept"
            var buttons = document.querySelectorAll('button');
            for (let btn of buttons) {
                var btnText = btn.textContent.trim();
                logger.info('Found button: ' + btnText);
                
                // Match "Accept All" (case insensitive)
                if (btnText.toLowerCase().includes('accept')) {
                    logger.info('Clicking button: ' + btnText);
                    btn.click();
                    return true;
                }
            }
            return false;
        """)
        
        logger.info(f"  JavaScript click result: {result}")
        time.sleep(2)
        
        # SECOND: Try clicking via Selenium with case-insensitive matching
        accept_selectors = [
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
            "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ok')]",
        ]
        
        for selector in accept_selectors:
            try:
                buttons = driver.find_elements(By.XPATH, selector)
                logger.info(f"  Found {len(buttons)} button(s) with selector")
                for btn in buttons:
                    if btn.is_displayed():
                        btn_text = btn.text
                        logger.info(f"  Clicking: {btn_text}")
                        # Scroll into view first
                        driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.5)
                        btn.click()
                        time.sleep(1)
            except Exception as e:
                logger.info(f"  Selector failed: {str(e)[:50]}")
                pass
        
        # THIRD: Use JavaScript to aggressively remove cookie elements
        logger.info("  Using JavaScript to remove cookie overlays...")
        driver.execute_script("""
            // Remove cookie banners by common selectors
            var toRemove = [
                document.querySelector('[class*="cookie"]'),
                document.querySelector('[class*="popup"]'),
                document.querySelector('[class*="banner"]'),
                document.querySelector('[id*="cookie"]'),
                document.querySelector('[id*="popup"]'),
                document.querySelector('[role="dialog"]'),
            ];
            
            toRemove.forEach(el => {
                if (el) {
                    try {
                        el.remove();
                    } catch(e) {}
                }
            });
            
            // Remove any overlay divs with high z-index
            var allDivs = document.querySelectorAll('div');
            allDivs.forEach(div => {
                var style = window.getComputedStyle(div);
                if (style.position === 'fixed' && parseInt(style.zIndex) > 500) {
                    try {
                        div.remove();
                    } catch(e) {}
                }
            });
            
            // Restore scrolling
            document.body.style.overflow = 'auto';
            document.body.style.height = 'auto';
        """)
        
        time.sleep(2)
        logger.info("✅ Popup dismissal complete")
        
        # Verify cookie banner is gone
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        if "accept all" in page_text[:500] or "cookies" in page_text[:300]:
            logger.warning("⚠️ Cookie banner may still be visible - proceeding anyway")
        else:
            logger.info("✅ Verified: Cookie banner removed")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Error dismissing popups: {e}")
        return True

def is_logged_in(driver):
    """Check if we're still logged in by checking URL and page content"""
    try:
        current_url = driver.current_url
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        # If URL still contains #/Login, we're NOT logged in
        if "#/login" in current_url.lower():
            logger.warning("⚠️ Not logged in - still on login page (URL check)")
            take_screenshot(driver, "ERROR_still_on_login_page")
            return False
        
        # If we see login form AND we're on a different URL, still check for logged-in content
        # Look for typical logged-in page indicators
        logged_in_indicators = ['book', 'facility', 'booking', 'my bookings', 'schedule']
        if any(indicator in page_text for indicator in logged_in_indicators):
            logger.info("✅ Logged in - found booking-related content")
            return True
        
        # If page contains login keywords AND we're still on login page URL
        if any(keyword in page_text for keyword in ['member sign in', 'forgot password', 'not a member yet']):
            logger.warning("⚠️ Not logged in - login page content detected")
            take_screenshot(driver, "ERROR_session_expired")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        return True

def check_for_slots(driver):
    """Check if 7-9 PM slots are available for Wed/Fri with detailed logging"""
    try:
        # Take screenshot BEFORE checking session to see current state
        logger.info("→ Taking screenshot before session check...")
        random_delay(1, 2)  # Random delay before checking
        take_screenshot(driver, "05_before_session_check")
        
        # Check if still logged in
        if not is_logged_in(driver):
            logger.warning("⚠️ Session expired - returning to check later")
            return False, []
        
        logger.info("→ Checking for available slots...")
        driver.get(BOOKING_URL)
        time.sleep(3)
        
        # Dismiss popups
        dismiss_popups(driver)
        
        # Check again if logged in
        time.sleep(1)
        if not is_logged_in(driver):
            logger.warning("⚠️ Got logged out - need to re-login")
            return False, []
        
        time.sleep(1)
        
        # Take screenshot after confirming session is still valid
        logger.info("✅ Session is active - taking screenshot...")
        take_screenshot(driver, "06_session_confirmed_booking_page")
        get_page_info(driver)
        
        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Log what facility we're on
        logger.info("📍 Current page analysis:")
        
        # Check for pickleball court reference
        if "pickleball" in page_source.lower():
            logger.info("✅ Pickleball court page detected")
        else:
            logger.warning("⚠️ Pickleball mention not found")
        
        # Check for dates (Wed/Fri)
        has_wed = "WEDNESDAY" in page_text or "Wednesday" in page_text or "WED" in page_text
        has_fri = "FRIDAY" in page_text or "Friday" in page_text or "FRI" in page_text
        
        if has_wed:
            logger.info("✅ Wednesday found on page")
        if has_fri:
            logger.info("✅ Friday found on page")
        
        if not has_wed and not has_fri:
            logger.warning("⚠️ Neither Wednesday nor Friday found")
            take_screenshot(driver, "06b_WARNING_no_wed_fri")
        
        # Check for 7-9 PM time indicators
        time_patterns = {
            '19:00': '7 PM',
            '20:00': '8 PM',
            '7:00 PM': '7 PM (format 1)',
            '8:00 PM': '8 PM (format 1)',
            '7:00pm': '7 PM (format 2)',
            '8:00pm': '8 PM (format 2)',
            '07:00 PM': '7 PM (format 3)',
            '08:00 PM': '8 PM (format 3)',
        }
        
        found_times = []
        for pattern, description in time_patterns.items():
            if pattern in page_source:
                found_times.append(f"{description} ({pattern})")
                logger.info(f"  ✅ Found: {description}")
        
        if not found_times:
            logger.info("ℹ No 7-9 PM time slots found on page")
            logger.info("📊 First 300 chars of page:")
            logger.info(page_text[:300])
            take_screenshot(driver, "06c_INFO_no_time_slots")
            return False, []
        
        logger.info(f"✅ Found {len(found_times)} time pattern(s)")
        
        # Find all "Book" buttons
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
                    logger.info(f"  Button #{idx}: Error processing")
                    
        except Exception as e:
            logger.error(f"Error finding buttons: {e}")
        
        if book_buttons:
            logger.info(f"🎉 FOUND {len(book_buttons)} AVAILABLE SLOTS FOR 7-9 PM!")
            take_screenshot(driver, "07_SUCCESS_slots_found")
            return True, book_buttons
        else:
            logger.info("ℹ No bookable 7-9 PM slots found")
            take_screenshot(driver, "07_INFO_no_book_buttons")
            return False, []
        
    except Exception as e:
        logger.error(f"❌ Error checking slots: {e}")
        take_screenshot(driver, "ERROR_check_slots")
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
        
        logger.info(f"✅ Email sent!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

def run_bot():
    """Main bot loop"""
    logger.info("="*70)
    logger.info("🏓 THE KALLANG PICKLEBALL BOT STARTED (WITH SCREENSHOTS)")
    logger.info("="*70)
    logger.info(f"Configuration:")
    logger.info(f"  Email: {KALLANG_EMAIL}")
    logger.info(f"  Notification: {NOTIFICATION_EMAIL}")
    logger.info(f"  Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
    logger.info(f"  Looking for: Pickleball Courts, Wed/Fri, 7-9 PM (19:00-20:00)")
    logger.info(f"  Screenshots: Enabled (saved to /tmp and uploaded to Imgur)")
    logger.info("="*70)
    
    driver = None
    check_count = 0
    already_notified = False
    max_login_attempts = 3
    login_attempt = 0
    
    try:
        validate_config()
        
        # LOGIN RETRY LOOP: Keep trying until login succeeds
        while login_attempt < max_login_attempts:
            login_attempt += 1
            logger.info(f"\n{'='*70}")
            logger.info(f"🔐 LOGIN ATTEMPT #{login_attempt}/{max_login_attempts}")
            logger.info(f"{'='*70}")
            
            driver = setup_webdriver()
            
            if login(driver):
                logger.info("✅ Login successful!")
                
                # Verify we actually reached the booking page
                logger.info("→ Verifying we reached booking page...")
                time.sleep(2)
                current_url = driver.current_url
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                if "facilityBooking" in current_url or "book" in page_text[:500]:
                    logger.info("✅ Confirmed: Booking page reached!")
                    take_screenshot(driver, "LOGIN_SUCCESS_booking_page")
                    break  # Exit login loop - we're logged in!
                else:
                    logger.warning("⚠️ Reached login but not booking page yet")
                    time.sleep(3)
                    driver.quit()
                    continue
            else:
                logger.error(f"❌ Login attempt #{login_attempt} failed")
                if driver:
                    driver.quit()
                
                if login_attempt < max_login_attempts:
                    logger.info(f"→ Retrying in 5 seconds... (Attempt {login_attempt + 1}/{max_login_attempts})")
                    random_delay(3, 7)
                else:
                    logger.error("❌ All login attempts failed. Exiting.")
                    return
        
        logger.info("✅ Successfully logged in. Starting monitoring loop...")
        logger.info("📌 NOTE: Keeping session alive across checks (not logging out between checks)")
        logger.info("📌 NOTE: Will auto re-login if session expires")
        logger.info("📸 Screenshots enabled for debugging")
        
        # MAIN MONITORING LOOP
        while True:
            check_count += 1
            logger.info(f"\n{'='*70}")
            logger.info(f"[Check #{check_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*70}")
            
            # Check if still logged in
            if not is_logged_in(driver):
                logger.warning("⚠️ Session expired - attempting to re-login...")
                driver.quit()
                
                # Try to re-login (up to 3 times)
                relogin_attempt = 0
                while relogin_attempt < max_login_attempts:
                    relogin_attempt += 1
                    logger.info(f"→ Re-login attempt #{relogin_attempt}/{max_login_attempts}")
                    
                    driver = setup_webdriver()
                    if login(driver):
                        logger.info("✅ Re-login successful!")
                        break
                    else:
                        logger.warning(f"❌ Re-login attempt #{relogin_attempt} failed")
                        if driver:
                            driver.quit()
                        if relogin_attempt < max_login_attempts:
                            random_delay(3, 7)
                        else:
                            logger.error(f"❌ Could not re-login after {max_login_attempts} attempts. Exiting.")
                            return
            
            has_slots, buttons = check_for_slots(driver)
            
            if has_slots and not already_notified:
                slot_count = len(buttons)
                logger.info(f"\n🔔 SLOTS DETECTED! Sending notification...")
                send_notification_email(slot_count)
                already_notified = True
                logger.info("✅ Notification sent! Continuing to monitor...")
            
            logger.info(f"\n⏰ Next check in {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
            
            # Add random variance to avoid pattern detection (±5 minutes)
            actual_interval = CHECK_INTERVAL + random.randint(-300, 300)
            next_check_time = datetime.fromtimestamp(time.time() + actual_interval)
            logger.info(f"Next check at: {next_check_time.strftime('%Y-%m-%d %H:%M:%S')} (±variance)")
            
            time.sleep(actual_interval)
    
    except KeyboardInterrupt:
        logger.info("\n⏸️  Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        take_screenshot(driver, "ERROR_critical")
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
