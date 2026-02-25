"""
The Kallang Pickleball Bot - Cloud Version with Screenshot Debugging
Maintains login session across multiple checks
Enhanced with screenshot debugging for troubleshooting
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
from email.mime.image import MIMEImage

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
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '3600'))

# CORRECT URLs for The Kallang (PerfectGym system)
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
        chrome_options.add_argument('--window-size=1920,1080')
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

def take_screenshot(driver, name="screenshot"):
    """Take a screenshot and save it with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/tmp/{name}_{timestamp}.png"
    
    try:
        driver.save_screenshot(filename)
        logger.info(f"📸 Screenshot saved: {filename}")
        return filename
    except Exception as e:
        logger.error(f"❌ Failed to take screenshot: {e}")
        return None

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

def dismiss_popups(driver):
    """Dismiss all popups and cookie dialogs - ULTRA AGGRESSIVE VERSION"""
    try:
        logger.info("→ Dismissing popups/cookies...")
        
        # Strategy 1: Wait for and click "Accept all" button explicitly
        accept_button_selectors = [
            (By.XPATH, "//button[contains(text(), 'Accept all')]"),
            (By.XPATH, "//button[contains(text(), 'Accept All')]"),
            (By.XPATH, "//button[contains(text(), 'ACCEPT ALL')]"),
            (By.XPATH, "//*[contains(text(), 'Accept all')]"),
            (By.CSS_SELECTOR, "button[class*='accept']"),
            (By.CSS_SELECTOR, "button[class*='Accept']"),
        ]
        
        button_clicked = False
        for selector_type, selector_value in accept_button_selectors:
            try:
                button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                logger.info(f"  ✅ Found Accept button: {selector_value}")
                button.click()
                logger.info(f"  ✅ Clicked Accept button!")
                button_clicked = True
                time.sleep(3)
                break
            except:
                continue
        
        if not button_clicked:
            logger.info("  → Accept button not found via Selenium, trying JavaScript...")
            # Strategy 2: JavaScript click on ANY button with "accept" text
            clicked = driver.execute_script("""
                var buttons = document.querySelectorAll('button, a, div[role="button"]');
                var clicked = false;
                for (let btn of buttons) {
                    var text = btn.textContent.toLowerCase();
                    if ((text.includes('accept all') || text.includes('accept')) 
                        && btn.offsetParent !== null) {
                        btn.click();
                        clicked = true;
                        console.log('Clicked: ' + btn.textContent);
                        break;
                    }
                }
                return clicked;
            """)
            
            if clicked:
                logger.info("  ✅ Clicked cookie accept button via JavaScript")
                time.sleep(3)
        
        # Strategy 3: FORCEFULLY remove ALL cookie-related elements
        logger.info("  → Forcefully removing cookie elements...")
        driver.execute_script("""
            // Remove ALL elements containing "cookie" in class or ID
            var cookieElements = document.querySelectorAll('[class*="cookie" i], [class*="Cookie" i], [id*="cookie" i], [id*="Cookie" i]');
            console.log('Found ' + cookieElements.length + ' cookie elements');
            cookieElements.forEach(el => {
                el.remove();
            });
            
            // Remove common modal/overlay patterns
            var overlays = document.querySelectorAll('[class*="overlay" i], [class*="modal" i], [class*="backdrop" i]');
            console.log('Found ' + overlays.length + ' overlay elements');
            overlays.forEach(el => {
                if (el.style.zIndex > 100) {
                    el.remove();
                }
            });
            
            // Remove any fixed-position divs with high z-index
            var allDivs = document.querySelectorAll('div');
            var removed = 0;
            allDivs.forEach(div => {
                var style = window.getComputedStyle(div);
                if (style.position === 'fixed' && parseInt(style.zIndex) > 500) {
                    var text = div.textContent.toLowerCase();
                    if (text.includes('cookie') || text.includes('accept')) {
                        div.remove();
                        removed++;
                    }
                }
            });
            console.log('Removed ' + removed + ' fixed elements');
            
            // Restore body scroll
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
        """)
        
        time.sleep(2)
        
        # Verify the cookie text is gone
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "Cookies" in page_text[:300]:
            logger.warning("  ⚠️ Cookie text still visible, trying one more time...")
            # Nuclear option: remove everything from the page that mentions cookies
            driver.execute_script("""
                var walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    null,
                    false
                );
                
                var nodesToRemove = [];
                while(walker.nextNode()) {
                    var node = walker.currentNode;
                    if (node.textContent.toLowerCase().includes('cookie') && 
                        node.textContent.length < 1000) {
                        nodesToRemove.push(node);
                    }
                }
                
                nodesToRemove.forEach(node => {
                    try {
                        node.remove();
                    } catch(e) {}
                });
            """)
            time.sleep(1)
            logger.info("  ✅ Nuclear cookie removal completed")
        else:
            logger.info("  ✅ Cookie banner successfully removed!")
        
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ Error dismissing popups: {e}")
        return True

def login(driver):
    """Login to The Kallang account with screenshot debugging"""
    try:
        logger.info("→ Attempting to login...")
        driver.get(LOGIN_URL)
        time.sleep(5)
        
        # Take screenshot of login page
        take_screenshot(driver, "01_login_page")
        get_page_info(driver)
        
        # Dismiss any popups
        dismiss_popups(driver)
        
        # Take screenshot AFTER cookie dismissal to verify
        take_screenshot(driver, "01b_after_cookie_dismiss")
        
        # Verify cookie banner is gone
        page_text_check = driver.find_element(By.TAG_NAME, "body").text
        if "Cookies" in page_text_check[:200]:
            logger.warning("⚠️ Cookie banner still visible, trying again...")
            dismiss_popups(driver)
            time.sleep(2)
        else:
            logger.info("✅ Cookie banner confirmed removed!")
        
        # Wait for login form to be fully visible
        logger.info("→ Waiting for login form to be visible...")
        time.sleep(3)
        
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
                logger.info(f"✅ Found email field with: {selector_value}")
                break
            except:
                continue
        
        if not email_field:
            logger.error("❌ Could not find email input field")
            take_screenshot(driver, "ERROR_no_email_field")
            return False
        
        # Take screenshot before entering credentials
        take_screenshot(driver, "02_before_credentials")
        
        # Log credentials being used (hide password)
        logger.info(f"  Using email: {KALLANG_EMAIL}")
        logger.info(f"  Using password: {'*' * len(KALLANG_PASSWORD)}")
        
        email_field.clear()
        email_field.send_keys(KALLANG_EMAIL)
        logger.info(f"✅ Email entered")
        time.sleep(2)
        
        # Find password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(KALLANG_PASSWORD)
        logger.info("✅ Password entered")
        time.sleep(2)
        
        # Take screenshot before clicking login
        take_screenshot(driver, "03_before_login_click")
        
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
        
        # Monitor URL changes
        initial_url = driver.current_url
        logger.info(f"  Before login - URL: {initial_url}")
        
        time.sleep(8)
        
        final_url = driver.current_url
        logger.info(f"  After login - URL: {final_url}")
        
        if initial_url != final_url:
            logger.info(f"✅ URL changed - likely logged in!")
        else:
            logger.warning(f"⚠️ URL unchanged - login might have failed")
        
        # Take screenshot after login
        take_screenshot(driver, "04_after_login")
        page_info = get_page_info(driver)
        
        # Check for error messages
        page_text = driver.find_element(By.TAG_NAME, "body").text
        error_keywords = ['invalid', 'incorrect', 'wrong', 'error', 'failed', 'denied']
        found_errors = [kw for kw in error_keywords if kw in page_text.lower()]
        
        if found_errors:
            logger.error(f"❌ Login error detected: {', '.join(found_errors)}")
            logger.error(f"📄 Full page text:")
            logger.error(page_text)
            take_screenshot(driver, "ERROR_login_error_message")
            return False
        
        # Verify we're logged in
        page_text_lower = page_text.lower()
        
        if "login" in page_text_lower and "forgot password" in page_text_lower:
            logger.warning("⚠️ Still on login page - login may have failed")
            take_screenshot(driver, "ERROR_still_on_login")
            time.sleep(5)
            # Check again after waiting
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "login" in page_text and "forgot password" in page_text:
                logger.error("❌ Login failed - still seeing login page")
                # Log the actual page content to see what's wrong
                logger.error(f"📄 Page content: {page_text[:1000]}")
                return False
        
        # Dismiss any post-login popups
        dismiss_popups(driver)
        
        logger.info("✅ Login process completed")
        take_screenshot(driver, "05_login_completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        take_screenshot(driver, "ERROR_login_exception")
        import traceback
        logger.error(traceback.format_exc())
        return False

def is_logged_in(driver):
    """Check if we're still logged in by checking page content"""
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        # If we see login-related text, we're NOT logged in
        if any(keyword in page_text for keyword in ['member sign in', 'login', 'forgot password', 'not a member yet']):
            logger.warning("⚠️ Not logged in - session expired")
            take_screenshot(driver, "ERROR_session_expired")
            return False
        
        return True
    except:
        return True

def check_for_slots(driver):
    """Check if 7-9 PM slots are available for Wed/Fri with detailed logging"""
    try:
        # Check if still logged in
        if not is_logged_in(driver):
            logger.warning("⚠️ Session expired - returning to check later")
            return False, []
        
        logger.info("→ Checking for available slots...")
        driver.get(BOOKING_URL)
        time.sleep(3)
        
        # Take screenshot of booking page
        take_screenshot(driver, "06_booking_page")
        get_page_info(driver)
        
        # Dismiss popups
        dismiss_popups(driver)
        
        # Check again if logged in
        time.sleep(1)
        if not is_logged_in(driver):
            logger.warning("⚠️ Got logged out - need to re-login")
            return False, []
        
        time.sleep(1)
        
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
            take_screenshot(driver, "WARNING_no_wed_fri")
        
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
            logger.info("ℹ️ No 7-9 PM time slots found on page")
            logger.info("📊 First 300 chars of page:")
            logger.info(page_text[:300])
            take_screenshot(driver, "INFO_no_time_slots")
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
            take_screenshot(driver, "SUCCESS_slots_found")
            return True, book_buttons
        else:
            logger.info("ℹ️ No bookable 7-9 PM slots found")
            take_screenshot(driver, "INFO_no_book_buttons")
            return False, []
        
    except Exception as e:
        logger.error(f"❌ Error checking slots: {e}")
        take_screenshot(driver, "ERROR_check_slots")
        import traceback
        logger.error(traceback.format_exc())
        return False, []

def send_notification_email(slot_count, screenshots=[]):
    """Send email notification with screenshots when slots are found"""
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
                        <a href="{BOOKING_URL}" class="button">BOOK NOW →</a>
                    </div>
                    
                    <p><strong>⏱️ Time is limited!</strong> Slots disappear fast.</p>
                    <p><small>Screenshots of available slots are attached to this email.</small></p>
                </div>
            </body>
        </html>
        """
        
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = GMAIL_SENDER
        msg['To'] = NOTIFICATION_EMAIL
        msg.attach(MIMEText(html_body, "html"))
        
        # Attach screenshots if available
        for screenshot_path in screenshots:
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment', 
                                 filename=os.path.basename(screenshot_path))
                    msg.attach(img)
                    logger.info(f"  📎 Attached: {os.path.basename(screenshot_path)}")
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, NOTIFICATION_EMAIL, msg.as_string())
        
        logger.info(f"✅ Email sent with {len(screenshots)} screenshot(s)!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

def run_bot():
    """Main bot loop"""
    logger.info("="*70)
    logger.info("🏓 THE KALLANG PICKLEBALL BOT - WITH SCREENSHOT DEBUG")
    logger.info("="*70)
    logger.info(f"Configuration:")
    logger.info(f"  Email: {KALLANG_EMAIL}")
    logger.info(f"  Notification: {NOTIFICATION_EMAIL}")
    logger.info(f"  Check interval: {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
    logger.info(f"  Looking for: Pickleball Courts, Wed/Fri, 7-9 PM (19:00-20:00)")
    logger.info(f"  Screenshots: Saved to /tmp/ and attached to emails")
    logger.info("="*70)
    
    driver = None
    check_count = 0
    already_notified = False
    
    try:
        validate_config()
        driver = setup_webdriver()
        
        if not login(driver):
            logger.error("❌ Failed to login. Exiting.")
            logger.error("📸 Check screenshots in /tmp/ for debugging")
            return
        
        logger.info("✅ Successfully logged in. Starting monitoring loop...")
        logger.info("📌 NOTE: Keeping session alive across checks")
        logger.info("📸 Screenshots will be taken at each step for debugging")
        
        while True:
            check_count += 1
            logger.info(f"\n{'='*70}")
            logger.info(f"[Check #{check_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*70}")
            
            has_slots, buttons = check_for_slots(driver)
            
            if has_slots and not already_notified:
                slot_count = len(buttons)
                logger.info(f"\n🔔 SLOTS DETECTED! Sending notification...")
                
                # Get latest screenshots to attach
                screenshots = []
                try:
                    for file in sorted(os.listdir('/tmp')):
                        if file.endswith('.png'):
                            screenshots.append(os.path.join('/tmp', file))
                    # Send the last 3 screenshots
                    screenshots = screenshots[-3:] if len(screenshots) > 3 else screenshots
                except:
                    pass
                
                send_notification_email(slot_count, screenshots)
                already_notified = True
                logger.info("✅ Notification sent! Continuing to monitor...")
            elif has_slots:
                logger.info("ℹ️ Slots still available (already notified)")
            else:
                logger.info("ℹ️ No available slots - will check again")
                already_notified = False
            
            logger.info(f"\n⏰ Next check in {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")
            logger.info(f"Next check at: {datetime.fromtimestamp(time.time() + CHECK_INTERVAL).strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(CHECK_INTERVAL)
    
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
