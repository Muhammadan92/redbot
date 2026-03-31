"""One-time setup: log into YouTube on the Android emulator and save the session."""

import os
import subprocess

from emulator_manager import start_emulator, start_appium, stop_appium
from mobile_driver import (
    create_appium_driver,
    find_element,
    navigate,
    save_cookies,
    wait,
)

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "youtube_session_mobile.json")


def save_youtube_session_mobile():
    # Start emulator with visible window so user can interact
    print("Starting Android emulator (with visible window)...")
    serial = start_emulator(headless=False)
    print(f"Emulator ready: {serial}")

    print("Starting Appium server...")
    start_appium()

    driver = None
    try:
        driver = create_appium_driver(device_serial=serial)
        driver.get("https://accounts.google.com/signin")

        print("")
        print("=" * 55)
        print("  LOG INTO GOOGLE ON THE EMULATOR")
        print("=" * 55)
        print("")
        print("  1. Log in with your Google account in the emulator")
        print("  2. Complete any 2FA if prompted")
        print("  3. Wait until you see the Google homepage")
        print("  4. Come back here and press ENTER")
        print("")
        print("=" * 55)

        input("Press ENTER when you are logged in... ")

        # Save cookies as backup
        save_cookies(driver, COOKIES_FILE)
        print(f"\nCookies saved to {COOKIES_FILE}")

        # Snapshot emulator state for fast restore
        try:
            adb_path = os.path.join(
                os.getenv("ANDROID_HOME", os.path.expanduser("~/Library/Android/sdk")),
                "platform-tools", "adb",
            )
            subprocess.run(
                [adb_path, "-s", serial, "emu", "avd", "snapshot", "save", "youtube_logged_in"],
                capture_output=True, timeout=30,
            )
            print("Emulator snapshot saved: youtube_logged_in")
        except Exception as e:
            print(f"Warning: Could not save emulator snapshot: {e}")

        # Verify login on YouTube
        navigate(driver, "https://m.youtube.com")
        wait(3000)

        avatar = find_element(driver, [
            "button.topbar-menu-button-avatar-button",
            "img.ytm-profile-thumbnail",
            "button[aria-label*='Account']",
            "button[aria-label*='account']",
        ], timeout=10000)

        if avatar:
            print("Verified: logged in to YouTube on mobile!")
            # Try to get channel name
            try:
                avatar.click()
                wait(2000)
                name_el = find_element(driver, [
                    ".account-name",
                    "yt-formatted-string.ytm-account-section-renderer",
                    ".channel-name",
                ], timeout=5000)
                if name_el:
                    channel = name_el.text.strip()
                    if channel:
                        print(f"Channel: {channel}")
            except Exception:
                pass
        else:
            print("WARNING: Could not verify YouTube login.")
            print("The cookies were saved anyway — try running the bot to see if it works.")

        print("\nDone! You can now start the bot with USE_MOBILE=true.")

    finally:
        if driver:
            driver.quit()
        stop_appium()
        # Don't stop the emulator — keep it running with the session intact


if __name__ == "__main__":
    save_youtube_session_mobile()
