"""One-time setup: log into YouTube/Google manually and save the session for the bot."""
import os
from playwright.sync_api import sync_playwright
from config import Config


def save_youtube_session():
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=os.path.join(os.path.dirname(__file__), ".chrome-profile-youtube"),
        headless=False,
        channel="chrome",
        args=["--disable-blink-features=AutomationControlled"],
        user_agent=Config.YOUTUBE_USER_AGENT,
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()

    page.goto("https://accounts.google.com/signin")

    print("=" * 55)
    print("  LOG INTO GOOGLE IN THE BROWSER WINDOW")
    print("=" * 55)
    print()
    print("  1. Log in with your Google account")
    print("  2. Complete any 2FA if prompted")
    print("  3. Wait until you see the Google homepage")
    print("  4. Come back here and press ENTER")
    print()
    print("=" * 55)

    input("Press ENTER when you are logged in... ")

    # Save session
    context.storage_state(path=os.path.join(os.path.dirname(__file__), "youtube_session.json"))
    print("\nSession saved to youtube_session.json")

    # Verify by navigating to YouTube
    page.goto("https://www.youtube.com", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Check for avatar button (indicates logged in)
    avatar = page.locator("button#avatar-btn, img.ytd-topbar-menu-button-renderer")
    if avatar.count() > 0:
        # Try to get channel name
        try:
            page.locator("button#avatar-btn").first.click()
            page.wait_for_timeout(1000)
            channel_el = page.locator("yt-formatted-string.ytd-account-item-renderer").first
            if channel_el.is_visible(timeout=3000):
                channel_name = (channel_el.text_content() or "").strip()
                print(f"Verified: logged in as {channel_name}")
            else:
                print("Verified: logged in to YouTube")
        except Exception:
            print("Verified: logged in to YouTube")
    else:
        print("WARNING: Could not verify YouTube login.")
        print("The session was saved anyway - try running the bot to see if it works.")

    context.close()
    pw.stop()
    print("\nDone! You can now start the bot with YouTube platform.")


if __name__ == "__main__":
    save_youtube_session()
