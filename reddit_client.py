import os
from playwright.sync_api import sync_playwright
from config import Config

SESSION_FILE = os.path.join(os.path.dirname(__file__), "reddit_session.json")


def _find_and_fill(page, selectors, value, field_name):
    """Try multiple selectors to find and fill an input field."""
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=3000):
                el.click()
                el.fill(value)
                return True
        except Exception:
            continue
    raise RuntimeError(f"Could not find {field_name} field. Tried: {selectors}")


def _find_and_click(page, selectors, label):
    """Try multiple selectors to find and click a button."""
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=3000):
                el.click()
                return True
        except Exception:
            continue
    raise RuntimeError(f"Could not find {label} button. Tried: {selectors}")


def create_session():
    """Load saved Reddit session, return (playwright, browser, page, username)."""
    if not os.path.exists(SESSION_FILE):
        raise RuntimeError(
            "No saved Reddit session found. Run 'python save_session.py' first to log in."
        )

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=Config.REDDIT_USER_AGENT,
        storage_state=SESSION_FILE,
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()

    # Verify login on old.reddit.com
    page.goto("https://old.reddit.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    username = None

    # Check for logout form (only present when logged in)
    logout = page.locator('form[action="https://old.reddit.com/logout"]')
    if logout.count() > 0:
        # Extract username from user span
        try:
            links = page.locator("span.user a")
            for i in range(links.count()):
                text = (links.nth(i).text_content() or "").strip().lower()
                if text and text not in ("log in", "login", "sign up", "register", "sign in"):
                    username = text
                    break
        except Exception:
            pass
        if not username:
            username = Config.REDDIT_USERNAME

    if not username:
        raise RuntimeError(
            "Saved session expired. Run 'python save_session.py' again to log in."
        )

    return pw, browser, page, username


def close_session(pw, browser):
    """Clean up Playwright browser resources."""
    try:
        browser.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass


def fetch_hot_posts(page, subreddit_name="all", limit=50):
    """Fetch hot posts from a subreddit using the browser session."""
    resp = page.context.request.get(
        f"https://www.reddit.com/r/{subreddit_name}/hot.json",
        params={"limit": str(limit), "raw_json": "1"},
    )
    if not resp.ok:
        raise RuntimeError(f"Failed to fetch posts: {resp.status} {resp.status_text}")

    data = resp.json()
    posts = []
    for child in data["data"]["children"]:
        post = child["data"]
        if post.get("stickied"):
            continue
        posts.append({
            "id": post["id"],
            "title": post["title"],
            "selftext": (post.get("selftext") or "")[:500],
            "url": post.get("url", ""),
            "subreddit": post.get("subreddit", ""),
            "num_comments": post.get("num_comments", 0),
            "permalink": post.get("permalink", ""),
        })
    return posts


def post_comment(page, submission_id, comment_text):
    """Post a comment on a Reddit submission using Playwright DOM interaction."""
    page.goto(
        f"https://old.reddit.com/comments/{submission_id}",
        wait_until="networkidle",
        timeout=30000,
    )
    page.wait_for_timeout(3000)

    # old.reddit.com uses standard <textarea> elements
    _find_and_fill(page, [
        'textarea[name="text"]',
        ".commentarea textarea",
        ".usertext-edit textarea",
        "form.usertext textarea",
    ], comment_text, "comment textarea")

    _find_and_click(page, [
        "button.save",
        'button:has-text("save")',
        ".usertext-buttons button",
        '.bottom-area button[type="submit"]',
    ], "save comment")

    page.wait_for_timeout(3000)
    return True
