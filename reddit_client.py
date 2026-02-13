import httpx
from playwright.sync_api import sync_playwright
from config import Config

BASE_HEADERS = {
    "User-Agent": Config.REDDIT_USER_AGENT,
}


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
    """Launch a browser, log into Reddit, return (playwright, browser, page, username)."""
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent=Config.REDDIT_USER_AGENT,
    )
    page = context.new_page()

    # Navigate to new Reddit login page
    page.goto("https://www.reddit.com/login", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)  # let JS render

    # Fill username - try multiple selectors
    _find_and_fill(page, [
        "#login-username",
        'input[name="username"]',
        'input[autocomplete="username"]',
        'input[type="text"]',
    ], Config.REDDIT_USERNAME, "username")

    # Fill password - try multiple selectors
    # (might be on same page or after clicking "Continue")
    password_selectors = [
        "#login-password",
        'input[name="password"]',
        'input[autocomplete="current-password"]',
        'input[type="password"]',
    ]

    try:
        _find_and_fill(page, password_selectors, Config.REDDIT_PASSWORD, "password")
    except RuntimeError:
        # Two-step flow: click Continue/Next first, then fill password
        _find_and_click(page, [
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button[type="submit"]',
        ], "Continue")
        page.wait_for_timeout(2000)
        _find_and_fill(page, password_selectors, Config.REDDIT_PASSWORD, "password")

    # Click Log In / Submit
    _find_and_click(page, [
        'button:has-text("Log In")',
        'button:has-text("Log in")',
        'button:has-text("Sign In")',
        'button[type="submit"]',
    ], "Login")

    # Wait for login to complete
    page.wait_for_timeout(5000)

    # Verify login by navigating to old.reddit.com (cookies carry over)
    page.goto("https://old.reddit.com", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Check for logged-in user element on old reddit
    user_link = page.locator(".user a").first
    try:
        if user_link.is_visible(timeout=5000):
            username = user_link.text_content() or Config.REDDIT_USERNAME
        else:
            raise RuntimeError("Login verification failed - not logged in on old.reddit.com")
    except Exception:
        raise RuntimeError("Login verification failed - could not confirm logged-in state")

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


def fetch_hot_posts(subreddit_name="all", limit=50):
    """Fetch hot posts from a subreddit using public JSON endpoint. No auth needed."""
    resp = httpx.get(
        f"https://www.reddit.com/r/{subreddit_name}/hot.json",
        params={"limit": limit, "raw_json": 1},
        headers=BASE_HEADERS,
        timeout=30.0,
    )
    resp.raise_for_status()

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
    """Post a comment on a Reddit submission using Playwright browser."""
    # Navigate to the post on old reddit
    page.goto(
        f"https://old.reddit.com/comments/{submission_id}",
        wait_until="domcontentloaded",
    )

    # Find the top-level comment textarea
    comment_form = page.locator(".commentarea .usertext-edit textarea").first
    comment_form.wait_for(state="visible", timeout=10000)
    comment_form.click()
    comment_form.fill(comment_text)

    # Click the save/submit button
    save_btn = page.locator(".commentarea .usertext-edit .save-button button").first
    save_btn.click()

    # Wait for the comment to appear (indicates success)
    page.wait_for_timeout(3000)

    return True
