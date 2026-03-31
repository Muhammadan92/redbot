"""Appium WebDriver wrapper with helpers that mirror the Playwright API surface."""

import json
import os
import random
import time

import requests
from appium import webdriver as appium_webdriver
from appium.options import UiAutomator2Options
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config


def create_appium_driver(device_serial=None):
    """Create and return an Appium WebDriver connected to Mobile Chrome on the emulator."""
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.browser_name = "Chrome"
    options.device_name = device_serial or f"emulator-{Config.EMULATOR_PORT}"
    options.no_reset = True
    options.set_capability("appium:chromedriverAutodownload", True)
    options.set_capability("appium:chromeOptions", {
        "args": ["--disable-blink-features=AutomationControlled"],
    })

    driver = appium_webdriver.Remote(
        command_executor=Config.APPIUM_HOST,
        options=options,
    )
    return driver


def find_element(driver, selectors, timeout=10000):
    """Try multiple CSS selectors to find a visible element. Returns element or None.

    Mirrors the Playwright _find_element pattern used throughout the codebase.
    """
    timeout_sec = timeout / 1000
    for selector in selectors:
        try:
            element = WebDriverWait(driver, timeout_sec).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
            )
            return element
        except (TimeoutException, NoSuchElementException, WebDriverException):
            continue
    return None


def find_elements(driver, selector):
    """Find all elements matching a CSS selector. Returns a list (empty if none found)."""
    try:
        return driver.find_elements(By.CSS_SELECTOR, selector)
    except WebDriverException:
        return []


def navigate(driver, url):
    """Navigate to a URL and wait for the page body to be present."""
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
    except TimeoutException:
        pass  # Page may still be usable


def swipe_up(driver, distance=800, duration_ms=500):
    """Perform a realistic touch swipe-up gesture on the screen."""
    size = driver.get_window_size()
    start_x = size["width"] // 2
    start_y = int(size["height"] * 0.7)
    end_y = max(int(size["height"] * 0.2), start_y - distance)

    driver.execute_script("mobile: swipeGesture", {
        "left": start_x - 50,
        "top": end_y,
        "width": 100,
        "height": start_y - end_y,
        "direction": "up",
        "percent": 0.75,
        "speed": int(distance / (duration_ms / 1000)),
    })


def scroll_down_js(driver, pixels=400):
    """Scroll down using JavaScript. Fallback when touch gestures don't work in Chrome."""
    driver.execute_script(f"window.scrollBy(0, {pixels})")


def human_type(element, text, min_delay_ms=30, max_delay_ms=80):
    """Type text character-by-character with random delays to mimic human typing."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.randint(min_delay_ms, max_delay_ms) / 1000)


def wait(ms):
    """Wait for the given number of milliseconds."""
    time.sleep(ms / 1000)


def get_cookies_session(driver, user_agent=None):
    """Extract cookies from the Appium driver and return a requests.Session.

    Useful for making HTTP API calls (e.g., Reddit JSON API) with the
    same authenticated session as the mobile browser.
    """
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(
            cookie["name"],
            cookie["value"],
            domain=cookie.get("domain", ""),
            path=cookie.get("path", "/"),
        )
    if user_agent:
        session.headers["User-Agent"] = user_agent
    return session


def save_cookies(driver, path):
    """Save the driver's cookies to a JSON file for backup/recovery."""
    cookies = driver.get_cookies()
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)


def load_cookies(driver, path, domain_url=None):
    """Load cookies from a JSON backup file into the driver.

    The driver must first navigate to a page on the target domain
    before cookies can be added (browser security requirement).
    """
    if not os.path.exists(path):
        return False

    with open(path) as f:
        cookies = json.load(f)

    if domain_url:
        driver.get(domain_url)
        wait(2000)

    for cookie in cookies:
        # Selenium requires at minimum name, value, and domain
        clean = {
            "name": cookie["name"],
            "value": cookie["value"],
        }
        if "domain" in cookie:
            clean["domain"] = cookie["domain"]
        if "path" in cookie:
            clean["path"] = cookie["path"]
        if "secure" in cookie:
            clean["secure"] = cookie["secure"]
        try:
            driver.add_cookie(clean)
        except WebDriverException:
            continue  # Skip cookies that fail (e.g., wrong domain)

    return True
