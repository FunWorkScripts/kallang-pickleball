import os
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverClick
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
LOGIN_URL = "https://members.myactivesg.com/auth"
BOOKING_URL = "https://members.myactivesg.com/facilities/venues/details/kallang"

def setup_webdriver():
    """Setup Chrome WebDriver with headless options"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver

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
        page_text = driver.find_element(By.TAG_NAME, "body").text[:500]  # First 500 chars
        
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
    """Dismiss any cookie banners or popups"""
    try:
        # Common cookie/popup button texts
        button_texts = ['Accept all', 'Accept', 'Agree', 'OK', 'Close', 'Got it', 'I agree']
        
        for text in button_texts:
            try:
                buttons = driver.find_elements(By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]")
                for btn in buttons:
                    if btn.is_displayed():
                        btn.click()
                        logger.info(f"✅ Clicked: {text}")
                        time.sleep(1)
            except:
                pass
        
        # JavaScript to remove cookie overlays
        driver.execute_script("""
            var elements = document.querySelectorAll('[class*="cookie"], [class*="popup"], [class*="banner"], [class*="modal"]');
            elements.forEach(el => {
                if (el) {
                    el.style.display = 'none';
                    el.remove();
                }
            });
            document.body.style.overflow = 'auto';
        """)
        
        logger.info("✅ Popup dismissal completed")
    except Exception as e:
        logger.warning(f"⚠️ Error dismissing popups: {e}")

def login(driver):
    """Login to The Kallang booking system"""
    try:
        logger.info("→ Navigating to login page...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        # Take screenshot of login page
        take_screenshot(driver, "01_login_page")
        get_page_info(driver)
        
        # Dismiss any popups
        dismiss_popups(driver)
        
        # Find email field (try multiple selectors)
        email_selectors = [
            "//input[@type='email']",
            "//input[@name='email']",
            "//input[@id='email']",
            "//input[@placeholder='Email']",
            "//input[contains(@class, 'email')]"
        ]
        
        email_field = None
        for selector in email_selectors:
            try:
                email_field = driver.find_element(By.XPATH, selector)
                if email_field:
                    logger.info(f"✅ Found email field with selector: {selector}")
                    break
            except:
                continue
        
        if not email_field:
            logger.error("❌ Could not find email field")
            take_screenshot(driver, "ERROR_no_email_field")
            return False
        
        # Enter credentials
        email = os.getenv('KALLANG_EMAIL')
        password = os.getenv('KALLANG_PASSWORD')
        
        email_field.clear()
        email_field.send_keys(email)
        logger.info("✅ Email entered")
        time.sleep(1)
        
        # Find password field
        password_field = driver.find_element(By.XPATH, "//input[@type='password']")
        password_field.clear()
        password_field.send_keys(password)
        logger.info("✅ Password entered")
        time.sleep(2)
        
        # Take screenshot before clicking login
        take_screenshot(driver, "02_before_login_click")
        
        # Find and click login button
        logger.info("→ Looking for login button...")
        login_clicked = False
        
        # Try multiple button selectors
        button_selectors = [
            "//button[@type='submit']",
            "//button[contains(text(), 'Sign in')]",
            "//button[contains(text(), 'Log in')]",
            "//button[contains(text(), 'Login')]",
            "//input[@type='submit']"
        ]
        
        for selector in button_selectors:
            try:
                button = driver.find_element(By.XPATH, selector)
                if button.is_displayed():
                    button.click()
                    logger.info(f"✅ Clicked login button: {selector}")
                    login_clicked = True
                    break
            except:
                continue
        
        # JavaScript fallback
        if not login_clicked:
            logger.info("→ Using JavaScript to click button...")
            driver.execute_script("""
                var buttons = document.querySelectorAll('button, input[type="submit"]');
                for (let btn of buttons) {
                    var text = btn.textContent.toLowerCase();
                    if (text.includes('sign in') || text.includes('login') || btn.type === 'submit') {
                        btn.click();
                        return true;
                    }
                }
            """)
            logger.info("✅ Clicked button via JavaScript")
        
        # Wait for page to load
        logger.info("→ Waiting for login to process...")
        time.sleep(8)
        
        # Take screenshot after login
        take_screenshot(driver, "03_after_login")
        page_info = get_page_info(driver)
        
        # Check if we're still on login page
        if page_info and 'sign in' in page_info['title'].lower():
            logger.warning("⚠️ Still on login page - login may have failed")
            take_screenshot(driver, "ERROR_still_on_login")
            return False
        
        # Dismiss any post-login popups
        dismiss_popups(driver)
        time.sleep(2)
        
        logger.info("✅ Login process completed")
        take_screenshot(driver, "04_login_completed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        take_screenshot(driver, "ERROR_login_exception")
        return False

def is_logged_in(driver):
    """Check if we're still logged in"""
    try:
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        
        # Keywords that indicate we're NOT logged in
        logout_keywords = ['sign in', 'member sign in', 'login', 'log in', 'forgot password']
        
        for keyword in logout_keywords:
            if keyword in page_text:
                logger.info(f"🔍 Found logout keyword: '{keyword}'")
                return False
        
        # Keywords that indicate we ARE logged in
        login_keywords = ['my account', 'logout', 'log out', 'profile', 'dashboard']
        
        for keyword in login_keywords:
            if keyword in page_text:
                logger.info(f"🔍 Found login keyword: '{keyword}'")
                return True
        
        # If no clear indicators, check URL
        current_url = driver.current_url.lower()
        if 'auth' in current_url or 'login' in current_url:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error checking login status: {e}")
        return False

def check_for_slots(driver):
    """Check for available Wed/Fri 7-9 PM pickleball slots"""
    try:
        # Check if we're still logged in
        if not is_logged_in(driver):
            logger.warning("⚠️ Not logged in - need to re-login")
            take_screenshot(driver, "ERROR_not_logged_in")
            return False, []
        
        logger.info("→ Navigating to booking page...")
        driver.get(BOOKING_URL)
        time.sleep(5)
        
        # Take screenshot of booking page
        take_screenshot(driver, "05_booking_page")
        get_page_info(driver)
        
        # Dismiss popups
        dismiss_popups(driver)
        time.sleep(2)
        
        # Get page source for analysis
        page_source = driver.page_source.lower()
        page_text = driver.find_element(By.TAG_NAME, "body").text
        
        logger.info("📍 Analyzing page content...")
        
        # Check for pickleball
        if 'pickleball' in page_source or 'pickleball' in page_text.lower():
            logger.info("✅ Pickleball courts page detected")
        else:
            logger.warning("⚠️ Pickleball not mentioned on page")
            logger.info(f"📊 Sample content: {page_text[:200]}")
        
        # Check for days
        has_wednesday = 'wednesday' in page_text.lower() or 'wed' in page_text.lower()
        has_friday = 'friday' in page_text.lower() or 'fri' in page_text.lower()
        
        if has_wednesday:
            logger.info("✅ Wednesday found on page")
        if has_friday:
            logger.info("✅ Friday found on page")
        
        if not has_wednesday and not has_friday:
            logger.warning("⚠️ Neither Wednesday nor Friday found")
            take_screenshot(driver, "WARNING_no_wed_fri")
            return False, []
        
        # Look for time patterns
        time_patterns = ['19:00', '20:00', '7:00 pm', '8:00 pm', '7pm', '8pm']
        found_times = []
        
        for pattern in time_patterns:
            if pattern in page_text.lower():
                logger.info(f"✅ Found time pattern: {pattern}")
                found_times.append(pattern)
        
        if not found_times:
            logger.info("ℹ️ No 7-9 PM time slots found in text")
            take_screenshot(driver, "INFO_no_time_slots")
            return False, []
        
        # Look for "Book" buttons
        book_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Book')]")
        logger.info(f"📊 Found {len(book_buttons)} 'Book' buttons on page")
        
        if len(book_buttons) > 0:
            logger.info("🎉 FOUND AVAILABLE SLOTS!")
            take_screenshot(driver, "SUCCESS_slots_found")
            return True, book_buttons
        
        logger.info("ℹ️ No available booking buttons found")
        take_screenshot(driver, "INFO_no_book_buttons")
        return False, []
        
    except Exception as e:
        logger.error(f"❌ Error checking slots: {e}")
        take_screenshot(driver, "ERROR_check_slots")
        return False, []

def send_notification_email(slot_count, screenshots=[]):
    """Send email notification with screenshots when slots are found"""
    try:
        sender = os.getenv('GMAIL_SENDER')
        password = os.getenv('GMAIL_APP_PASSWORD')
        recipient = os.getenv('NOTIFICATION_EMAIL')
        
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = f"🏓 KALLANG PICKLEBALL - {slot_count} SLOTS FOUND!"
        
        body = f"""
        <html>
        <body>
            <h2>🎉 Pickleball Slots Available!</h2>
            <p><strong>{slot_count}</strong> booking slots found for Wednesday/Friday 7-9 PM!</p>
            
            <p><strong>Book now:</strong></p>
            <p><a href="{BOOKING_URL}" style="background-color: #4CAF50; color: white; padding: 15px 32px; text-decoration: none; display: inline-block; font-size: 16px; margin: 4px 2px; border-radius: 8px;">
                🏓 BOOK NOW
            </a></p>
            
            <p><small>This is an automated notification from your Kallang Pickleball Bot</small></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach screenshots if available
        for screenshot_path in screenshots:
            if os.path.exists(screenshot_path):
                with open(screenshot_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(screenshot_path))
                    msg.attach(img)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender, password)
            server.send_message(msg)
        
        logger.info("✅ Notification email sent!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email error: {e}")
        return False

def run_bot():
    """Main bot loop"""
    # Validate environment variables
    required_vars = ['KALLANG_EMAIL', 'KALLANG_PASSWORD', 'NOTIFICATION_EMAIL', 'GMAIL_SENDER', 'GMAIL_APP_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return
    
    check_interval = int(os.getenv('CHECK_INTERVAL', 3600))
    
    logger.info("======================================================================")
    logger.info("🏓 KALLANG PICKLEBALL BOT - WITH SCREENSHOT DEBUG")
    logger.info("======================================================================")
    logger.info(f"Configuration:")
    logger.info(f"Email: {os.getenv('KALLANG_EMAIL')}")
    logger.info(f"Notification: {os.getenv('NOTIFICATION_EMAIL')}")
    logger.info(f"Check interval: {check_interval} seconds ({check_interval//60} minutes)")
    logger.info(f"Looking for: Pickleball Courts, Wed/Fri, 7-9 PM (19:00-20:00)")
    logger.info(f"Screenshots saved to: /tmp/")
    logger.info("======================================================================")
    
    # Setup WebDriver
    driver = setup_webdriver()
    logger.info("✅ Chrome WebDriver initialized")
    
    # Login once at startup
    if not login(driver):
        logger.error("❌ Initial login failed - check screenshots in /tmp/")
        driver.quit()
        return
    
    logger.info("✅ Successfully logged in. Starting monitoring loop...")
    logger.info("📌 NOTE: Keeping session alive across checks (not logging out between checks)")
    logger.info("📸 Screenshots available at: /tmp/*.png")
    
    check_count = 0
    already_notified = False
    
    try:
        while True:
            check_count += 1
            logger.info(f"\n======================================================================")
            logger.info(f"[Check #{check_count}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"======================================================================")
            
            has_slots, book_buttons = check_for_slots(driver)
            
            if has_slots and not already_notified:
                logger.info(f"🎉 FOUND {len(book_buttons)} AVAILABLE SLOTS FOR 7-9 PM!")
                logger.info("→ Sending notification email...")
                
                # Get latest screenshots
                screenshots = []
                for file in os.listdir('/tmp'):
                    if file.endswith('.png'):
                        screenshots.append(os.path.join('/tmp', file))
                
                if send_notification_email(len(book_buttons), screenshots[-3:]):  # Send last 3 screenshots
                    already_notified = True
                    logger.info("✅ Email sent with screenshots!")
            elif has_slots:
                logger.info("ℹ️ Slots still available (already notified)")
            else:
                logger.info("ℹ️ No available slots found - will check again")
                already_notified = False
            
            # Wait before next check
            logger.info(f"\n⏰ Next check in {check_interval} seconds ({check_interval//60} minutes)")
            logger.info(f"Next check at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        take_screenshot(driver, "ERROR_unexpected")
    finally:
        driver.quit()
        logger.info("✅ WebDriver closed")

if __name__ == "__main__":
    run_bot()
