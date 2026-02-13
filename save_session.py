"""One-time setup: log into Reddit manually and save the session for the bot."""
import os
from playwright.sync_api import sync_playwright
from config import Config


def save_reddit_session():
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=os.path.join(os.path.dirname(__file__), ".chrome-profile"),
        headless=False,
        channel="chrome",
        args=["--disable-blink-features=AutomationControlled"],
        user_agent=Config.REDDIT_USER_AGENT,
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()

    page.goto("https://www.reddit.com/login")

    print("=" * 55)
    print("  LOG INTO REDDIT IN THE BROWSER WINDOW")
    print("=" * 55)
    print()
    print("  1. Log in with your Reddit account")
    print("  2. Complete any CAPTCHA / 2FA if prompted")
    print("  3. Wait until you see your Reddit homepage")
    print("  4. Come back here and press ENTER")
    print()
    print("=" * 55)

    input("Press ENTER when you are logged in... ")

    # Save session
    context.storage_state(path="reddit_session.json")
    print("\nSession saved to reddit_session.json")

    # Verify it works on old.reddit.com
    page.goto("https://old.reddit.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    logout = page.locator('form[action="https://old.reddit.com/logout"]')
    if logout.count() > 0:
        # Try to get username
        try:
            links = page.locator("span.user a")
            for i in range(links.count()):
                text = (links.nth(i).text_content() or "").strip().lower()
                if text and text not in ("log in", "login", "sign up", "register", "sign in"):
                    print(f"Verified: logged in as u/{text}")
                    break
            else:
                print(f"Verified: logged in (username: {Config.REDDIT_USERNAME})")
        except Exception:
            print(f"Verified: logged in (username: {Config.REDDIT_USERNAME})")
    else:
        print("WARNING: Could not verify login on old.reddit.com.")
        print("The session was saved anyway - try running the bot to see if it works.")

    context.close()
    pw.stop()
    print("\nDone! You can now start the bot.")


if __name__ == "__main__":
    save_reddit_session()
