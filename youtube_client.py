import os
import re
import random
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from config import Config

SESSION_FILE = os.path.join(os.path.dirname(__file__), "youtube_session.json")


def _find_element(page, selectors, timeout=5000):
    """Try multiple selectors, return the first visible element or None."""
    for selector in selectors:
        try:
            el = page.locator(selector).first
            if el.is_visible(timeout=timeout):
                return el
        except Exception:
            continue
    return None


def create_session():
    """Load saved YouTube session, return (playwright, browser, page, channel_name)."""
    if not os.path.exists(SESSION_FILE):
        raise RuntimeError(
            "No saved YouTube session found. Run 'python save_youtube_session.py' first to log in."
        )

    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    context = browser.new_context(
        user_agent=Config.YOUTUBE_USER_AGENT,
        storage_state=SESSION_FILE,
    )
    context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    page = context.new_page()

    # Verify login
    page.goto("https://www.youtube.com", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    channel_name = None
    avatar = _find_element(page, [
        "button#avatar-btn",
        "img.ytd-topbar-menu-button-renderer",
    ], timeout=5000)

    if avatar:
        channel_name = "YouTube User"
        try:
            avatar.click()
            page.wait_for_timeout(1000)
            channel_el = page.locator("yt-formatted-string.ytd-account-item-renderer").first
            if channel_el.is_visible(timeout=3000):
                channel_name = (channel_el.text_content() or "").strip() or channel_name
            # Close the menu
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass
    else:
        raise RuntimeError(
            "Saved YouTube session expired. Run 'python save_youtube_session.py' again to log in."
        )

    return pw, browser, page, channel_name


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


def fetch_videos(page, source="search", topic="", video_urls=None, limit=20):
    """Fetch videos based on source mode. Returns list of video dicts."""
    if source == "search":
        return _fetch_by_search(page, topic, limit)
    elif source == "trending":
        return _fetch_trending(page, limit)
    elif source == "urls":
        return _fetch_by_urls(page, video_urls or [])
    else:
        raise ValueError(f"Unknown video source: {source}")


def _parse_renderers(page, limit, include_description=False):
    """Parse video renderer elements from the current page into video dicts."""
    videos = []
    # Try standard renderer first, fall back to rich grid layout (trending page)
    renderers = page.locator("ytd-video-renderer")
    if renderers.count() == 0:
        renderers = page.locator("ytd-rich-item-renderer ytd-rich-grid-media")
    count = min(renderers.count(), limit)

    for i in range(count):
        try:
            renderer = renderers.nth(i)
            title_el = renderer.locator("#video-title").first
            title = (title_el.get_attribute("title") or title_el.text_content() or "").strip()
            href = title_el.get_attribute("href") or ""
            video_id = _extract_video_id(href)
            if not video_id:
                continue

            channel_el = renderer.locator("ytd-channel-name yt-formatted-string a").first
            channel = ""
            try:
                channel = (channel_el.text_content() or "").strip()
            except Exception:
                pass

            description = ""
            if include_description:
                desc_el = renderer.locator("yt-formatted-string.metadata-snippet-text").first
                try:
                    description = (desc_el.text_content() or "").strip()
                except Exception:
                    pass

            videos.append({
                "id": video_id,
                "title": title,
                "description": description[:500],
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })
        except Exception:
            continue

    return videos


def _fetch_by_search(page, topic, limit):
    """Search YouTube for recent videos on a topic."""
    query = quote_plus(topic)
    # sp=CAISBAgBEAE filters to: Upload date = Last hour, Sort by = Relevance
    page.goto(
        f"https://www.youtube.com/results?search_query={query}&sp=CAISBAgBEAE",
        wait_until="domcontentloaded",
    )
    page.wait_for_timeout(3000)

    # Scroll to load more results
    for _ in range(3):
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1000)

    return _parse_renderers(page, limit, include_description=True)


def _fetch_trending(page, limit):
    """Fetch videos from YouTube trending page."""
    page.goto("https://www.youtube.com/feed/trending", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Scroll to load more
    for _ in range(3):
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(1000)

    return _parse_renderers(page, limit, include_description=False)


def _fetch_by_urls(page, video_urls):
    """Fetch video info from user-provided URLs."""
    videos = []
    for url in video_urls:
        url = url.strip()
        if not url:
            continue
        video_id = _extract_video_id(url)
        if not video_id:
            continue

        try:
            page.goto(
                f"https://www.youtube.com/watch?v={video_id}",
                wait_until="domcontentloaded",
            )
            page.wait_for_timeout(3000)

            title = ""
            title_el = _find_element(page, [
                "h1.ytd-watch-metadata yt-formatted-string",
                "h1.ytd-video-primary-info-renderer yt-formatted-string",
                "#title h1 yt-formatted-string",
            ], timeout=5000)
            if title_el:
                title = (title_el.text_content() or "").strip()

            description = ""
            # Try to expand description
            desc_btn = _find_element(page, [
                "tp-yt-paper-button#expand",
                "#description-inline-expander tp-yt-paper-button",
                "#expand",
            ], timeout=3000)
            if desc_btn:
                try:
                    desc_btn.click()
                    page.wait_for_timeout(1000)
                except Exception:
                    pass
            desc_el = _find_element(page, [
                "#description-inline-expander yt-attributed-string",
                "#description yt-formatted-string",
                "ytd-text-inline-expander yt-attributed-string",
            ], timeout=3000)
            if desc_el:
                description = (desc_el.text_content() or "").strip()

            channel = ""
            channel_el = _find_element(page, [
                "ytd-channel-name yt-formatted-string a",
                "#channel-name yt-formatted-string a",
            ], timeout=3000)
            if channel_el:
                channel = (channel_el.text_content() or "").strip()

            videos.append({
                "id": video_id,
                "title": title,
                "description": description[:500],
                "channel": channel,
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })
        except Exception:
            continue

    return videos


def _extract_video_id(url_or_href):
    """Extract video ID from a YouTube URL or href."""
    if not url_or_href:
        return None
    # /watch?v=VIDEO_ID
    match = re.search(r"[?&]v=([a-zA-Z0-9_-]{11})", url_or_href)
    if match:
        return match.group(1)
    # /shorts/VIDEO_ID or /live/VIDEO_ID
    match = re.search(r"/(?:shorts|live)/([a-zA-Z0-9_-]{11})", url_or_href)
    if match:
        return match.group(1)
    # youtu.be/VIDEO_ID
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url_or_href)
    if match:
        return match.group(1)
    # Bare video ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url_or_href.strip()):
        return url_or_href.strip()
    return None


def post_comment(page, video_id, comment_text):
    """Post a comment on a YouTube video using Playwright DOM interaction."""
    page.goto(
        f"https://www.youtube.com/watch?v={video_id}",
        wait_until="domcontentloaded",
    )

    # Wait for video page to load
    _find_element(page, ["ytd-watch-flexy", "#player"], timeout=15000)

    # Simulate watching: random wait 8-20s
    watch_time = random.randint(8, 20)
    page.wait_for_timeout(watch_time * 1000)

    # Scroll down gradually to trigger comments lazy-load
    for _ in range(4):
        page.mouse.wheel(0, random.randint(200, 400))
        page.wait_for_timeout(random.randint(500, 1500))

    # Wait for comments section to load
    comments_section = _find_element(page, [
        "ytd-comments#comments",
        "#comments",
    ], timeout=15000)

    if not comments_section:
        raise RuntimeError("Comments section did not load")

    # Check if comments are disabled
    disabled = _find_element(page, [
        "ytd-message-renderer #message",
    ], timeout=3000)
    if disabled:
        text = (disabled.text_content() or "").lower()
        if "disabled" in text or "turned off" in text:
            raise RuntimeError("Comments are disabled on this video")

    # Click comment placeholder to activate the comment box
    placeholder = _find_element(page, [
        "ytd-comment-simplebox-renderer #placeholder-area",
        "ytd-comment-simplebox-renderer #simplebox-placeholder",
        "#simple-box #placeholder-area",
    ], timeout=10000)

    if not placeholder:
        raise RuntimeError("Could not find comment box placeholder")

    placeholder.click()
    page.wait_for_timeout(1500)

    # Wait for the contenteditable input to appear
    editor = _find_element(page, [
        "#contenteditable-root",
        "div#contenteditable-root[contenteditable='true']",
        "#creation-box #contenteditable-root",
    ], timeout=10000)

    if not editor:
        raise RuntimeError("Could not find comment editor")

    # Type comment using page.type() for contenteditable compatibility
    editor.click()
    page.wait_for_timeout(500)
    page.keyboard.type(comment_text, delay=random.randint(30, 80))
    page.wait_for_timeout(1000)

    # Click submit button
    submit = _find_element(page, [
        "#submit-button",
        "ytd-button-renderer#submit-button",
        "#submit-button tp-yt-paper-button",
        "#submit-button button",
    ], timeout=5000)

    if not submit:
        raise RuntimeError("Could not find submit button")

    submit.click()
    page.wait_for_timeout(3000)

    return True
