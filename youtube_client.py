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


# ──────────────────────────────────────────────────────────────────────
#  MOBILE (Appium + Android Emulator) variants
# ──────────────────────────────────────────────────────────────────────

MOBILE_SESSION_FILE = os.path.join(os.path.dirname(__file__), "youtube_session_mobile.json")


def create_session_mobile():
    """Start emulator + Appium, open Mobile Chrome, verify YouTube login.

    Returns (driver, channel_name).
    """
    from emulator_manager import start_emulator, start_appium
    from mobile_driver import (
        create_appium_driver,
        find_element as mfind,
        load_cookies,
        navigate,
        wait,
    )

    serial = start_emulator()
    start_appium()
    driver = create_appium_driver(device_serial=serial)

    # If Chrome isn't logged in, try restoring cookies from backup
    navigate(driver, "https://m.youtube.com")
    wait(3000)

    avatar = mfind(driver, [
        "button.topbar-menu-button-avatar-button",
        "img.ytm-profile-thumbnail",
        "button[aria-label*='Account']",
        "button[aria-label*='account']",
    ], timeout=8000)

    if not avatar and os.path.exists(MOBILE_SESSION_FILE):
        load_cookies(driver, MOBILE_SESSION_FILE, domain_url="https://m.youtube.com")
        navigate(driver, "https://m.youtube.com")
        wait(3000)
        avatar = mfind(driver, [
            "button.topbar-menu-button-avatar-button",
            "img.ytm-profile-thumbnail",
            "button[aria-label*='Account']",
            "button[aria-label*='account']",
        ], timeout=8000)

    if not avatar:
        raise RuntimeError(
            "YouTube mobile session not logged in. "
            "Run 'python save_youtube_session_mobile.py' first."
        )

    channel_name = "YouTube User"
    try:
        avatar.click()
        wait(2000)
        from mobile_driver import find_element as mfind2
        name_el = mfind2(driver, [
            ".account-name",
            "yt-formatted-string.ytm-account-section-renderer",
            ".channel-name",
        ], timeout=5000)
        if name_el:
            channel_name = name_el.text.strip() or channel_name
        # Close the menu by navigating back
        driver.back()
        wait(1000)
    except Exception:
        pass

    return driver, channel_name


def close_session_mobile(driver):
    """Clean up Appium driver and optionally stop emulator."""
    try:
        driver.quit()
    except Exception:
        pass


def fetch_videos_mobile(driver, source="search", topic="", video_urls=None, limit=20):
    """Fetch videos on mobile YouTube based on source mode."""
    if source == "search":
        return _fetch_by_search_mobile(driver, topic, limit)
    elif source == "trending":
        return _fetch_trending_mobile(driver, limit)
    elif source == "urls":
        return _fetch_by_urls_mobile(driver, video_urls or [])
    else:
        raise ValueError(f"Unknown video source: {source}")


def _parse_renderers_mobile(driver, limit, include_description=False):
    """Parse video elements from the current mobile YouTube page."""
    from mobile_driver import find_elements, wait

    videos = []

    # Mobile YouTube uses different renderers depending on the page
    renderer_selectors = [
        "ytm-compact-video-renderer",
        "ytm-video-with-context-renderer",
        "ytm-rich-item-renderer",
        ".large-media-item",
        ".compact-media-item",
    ]

    renderers = []
    for sel in renderer_selectors:
        renderers = find_elements(driver, sel)
        if renderers:
            break

    count = min(len(renderers), limit)

    for i in range(count):
        try:
            renderer = renderers[i]

            # Extract title
            title = ""
            title_els = renderer.find_elements(
                "css selector",
                ".media-item-headline span, "
                "h3 .yt-core-attributed-string, "
                ".compact-media-item-headline span, "
                "h3 span"
            )
            for tel in title_els:
                t = (tel.text or "").strip()
                if t:
                    title = t
                    break

            # Extract video link / ID
            video_id = None
            link_els = renderer.find_elements(
                "css selector",
                "a[href*='watch'], "
                "a.media-item-thumbnail-container, "
                "a.compact-media-item-image"
            )
            for lel in link_els:
                href = lel.get_attribute("href") or ""
                vid = _extract_video_id(href)
                if vid:
                    video_id = vid
                    break

            if not video_id:
                continue

            # Extract channel name
            channel = ""
            ch_els = renderer.find_elements(
                "css selector",
                ".media-item-byline span, "
                ".ytm-badge-and-byline-renderer span, "
                ".compact-media-item-byline span"
            )
            for cel in ch_els:
                c = (cel.text or "").strip()
                if c and c not in ("·", "•", ""):
                    channel = c
                    break

            # Extract description snippet (search results only)
            description = ""
            if include_description:
                desc_els = renderer.find_elements(
                    "css selector",
                    ".media-item-description span, "
                    ".metadata-snippet-text span"
                )
                for del_ in desc_els:
                    d = (del_.text or "").strip()
                    if d:
                        description = d
                        break

            videos.append({
                "id": video_id,
                "title": title,
                "description": description[:500],
                "channel": channel,
                "url": f"https://m.youtube.com/watch?v={video_id}",
            })
        except Exception:
            continue

    return videos


def _fetch_by_search_mobile(driver, topic, limit):
    """Search YouTube mobile for recent videos on a topic."""
    from mobile_driver import navigate, swipe_up, wait

    query = quote_plus(topic)
    navigate(driver, f"https://m.youtube.com/results?search_query={query}&sp=CAISBAgBEAE")
    wait(3000)

    # Swipe to load more results
    for _ in range(3):
        swipe_up(driver, distance=random.randint(600, 1000))
        wait(random.randint(800, 1500))

    return _parse_renderers_mobile(driver, limit, include_description=True)


def _fetch_trending_mobile(driver, limit):
    """Fetch videos from YouTube mobile trending page."""
    from mobile_driver import navigate, swipe_up, wait

    navigate(driver, "https://m.youtube.com/feed/trending")
    wait(3000)

    for _ in range(3):
        swipe_up(driver, distance=random.randint(600, 1000))
        wait(random.randint(800, 1500))

    return _parse_renderers_mobile(driver, limit, include_description=False)


def _fetch_by_urls_mobile(driver, video_urls):
    """Fetch video info from user-provided URLs on mobile YouTube."""
    from mobile_driver import find_element as mfind, navigate, wait

    videos = []
    for url in video_urls:
        url = url.strip()
        if not url:
            continue
        video_id = _extract_video_id(url)
        if not video_id:
            continue

        try:
            navigate(driver, f"https://m.youtube.com/watch?v={video_id}")
            wait(3000)

            # Title
            title = ""
            title_el = mfind(driver, [
                "h2.slim-video-information-title .yt-core-attributed-string",
                "h2.slim-video-information-title span",
                "#video-title",
                ".slim-video-information-title",
            ], timeout=5000)
            if title_el:
                title = (title_el.text or "").strip()

            # Description — tap to expand
            description = ""
            expand = mfind(driver, [
                "ytm-expandable-video-description-body-renderer",
                ".slim-video-metadata-section",
            ], timeout=3000)
            if expand:
                try:
                    expand.click()
                    wait(1500)
                except Exception:
                    pass
            desc_el = mfind(driver, [
                "ytm-expandable-video-description-body-renderer .yt-core-attributed-string",
                ".description-content .yt-core-attributed-string",
                "#description-content",
            ], timeout=3000)
            if desc_el:
                description = (desc_el.text or "").strip()

            # Channel name
            channel = ""
            ch_el = mfind(driver, [
                ".slim-owner-channel-name",
                ".ytm-slim-owner-renderer span",
                ".channel-name",
            ], timeout=3000)
            if ch_el:
                channel = (ch_el.text or "").strip()

            videos.append({
                "id": video_id,
                "title": title,
                "description": description[:500],
                "channel": channel,
                "url": f"https://m.youtube.com/watch?v={video_id}",
            })
        except Exception:
            continue

    return videos


def post_comment_mobile(driver, video_id, comment_text):
    """Post a comment on a YouTube video using Appium on mobile Chrome."""
    from mobile_driver import (
        find_element as mfind,
        human_type,
        navigate,
        swipe_up,
        wait,
    )

    navigate(driver, f"https://m.youtube.com/watch?v={video_id}")

    # Wait for video page / player to load
    mfind(driver, ["#player", ".player-container", "video"], timeout=15000)

    # Simulate watching: random wait 8-20s
    watch_time = random.randint(8, 20)
    wait(watch_time * 1000)

    # Swipe down gradually to reach comments section
    for _ in range(4):
        swipe_up(driver, distance=random.randint(200, 400))
        wait(random.randint(500, 1500))

    # On mobile YouTube, comments may be behind a "Comments" header/button
    # that needs to be tapped to expand into a bottom sheet
    comments_header = mfind(driver, [
        "ytm-comment-section-renderer",
        "#comment-section-renderer",
        "ytm-comments-entry-point-header-renderer",
        ".comment-section-header",
    ], timeout=15000)

    if not comments_header:
        raise RuntimeError("Comments section did not load")

    # Tap to open comments panel (mobile uses a bottom sheet overlay)
    try:
        comments_header.click()
        wait(2000)
    except Exception:
        pass

    # Check if comments are disabled
    from mobile_driver import find_elements
    disabled_els = find_elements(driver, "ytm-message-renderer, .comments-disabled-message")
    for el in disabled_els:
        text = (el.text or "").lower()
        if "disabled" in text or "turned off" in text:
            raise RuntimeError("Comments are disabled on this video")

    # Find and tap "Add a comment..." placeholder
    placeholder = mfind(driver, [
        "ytm-comment-simplebox-renderer",
        ".comment-simplebox",
        "[placeholder*='comment']",
        "div[role='textbox']",
    ], timeout=10000)

    if not placeholder:
        raise RuntimeError("Could not find comment box placeholder")

    placeholder.click()
    wait(1500)

    # Find the actual editable input
    editor = mfind(driver, [
        "div[contenteditable='true']",
        "#contenteditable-root",
        "textarea",
    ], timeout=10000)

    if not editor:
        raise RuntimeError("Could not find comment editor")

    # Type the comment character-by-character
    editor.click()
    wait(500)
    human_type(editor, comment_text, min_delay_ms=30, max_delay_ms=80)
    wait(1000)

    # Find and tap the submit/send button
    submit = mfind(driver, [
        "button[aria-label*='Send']",
        "button[aria-label*='submit']",
        "button[aria-label*='Comment']",
        ".submit-button",
        "#submit-button",
    ], timeout=5000)

    if not submit:
        raise RuntimeError("Could not find submit button")

    submit.click()
    wait(3000)

    return True
