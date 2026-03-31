import threading
import time
import random
import json
import queue
from datetime import datetime
from reddit_client import create_session as reddit_create_session, close_session as reddit_close_session, fetch_hot_posts, post_comment as reddit_post_comment
from youtube_client import create_session as youtube_create_session, close_session as youtube_close_session, fetch_videos, post_comment as youtube_post_comment
from ai_client import classify_post, generate_comment

VIDEO_SOURCE_LABELS = {"search": "search", "trending": "trending", "urls": "URLs"}


class MessageAnnouncer:
    """Simple SSE broadcaster. Listeners receive messages via queues."""

    def __init__(self):
        self.listeners = []

    def listen(self):
        q = queue.Queue(maxsize=50)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        for i in reversed(range(len(self.listeners))):
            try:
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]


def format_sse(data, event=None):
    msg = f"data: {data}\n\n"
    if event:
        msg = f"event: {event}\n{msg}"
    return msg


class BotEngine:
    def __init__(self, announcer):
        self.announcer = announcer
        self._stop_event = threading.Event()
        self._thread = None
        self.is_running = False

        self.platform = "reddit"
        self.topic = ""
        self.subreddit = "all"
        self.comment_flavor = ""
        self.must_include = ""
        self.max_comments = 0  # 0 = unlimited
        self.delay_seconds = 30
        self.random_offset = 10
        self.dry_run = False
        self.comments_posted = 0
        self.commented_ids = set()

        # YouTube-specific
        self.video_source = "search"
        self.video_urls = []

    def log(self, message, level="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        data = json.dumps({
            "time": timestamp,
            "level": level,
            "message": message,
        })
        self.announcer.announce(format_sse(data, event="log"))

    def start(self, settings):
        if self.is_running:
            return False

        # Wait for previous thread to fully finish before starting a new one
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=10)

        self.platform = settings.get("platform", "reddit")
        self.topic = settings.get("topic", "").strip()
        self.subreddit = settings.get("subreddit", "all").strip() or "all"
        self.comment_flavor = settings["comment_flavor"]
        self.must_include = settings.get("must_include", "")
        self.must_include_context = settings.get("must_include_context", "")
        self.max_comments = int(settings.get("max_comments", 0))
        self.delay_seconds = int(settings.get("delay_seconds", 30))
        self.random_offset = int(settings.get("random_offset", 10))
        self.dry_run = settings.get("dry_run", False)
        self.comments_posted = 0
        self.commented_ids = set()

        # YouTube-specific settings
        self.video_source = settings.get("video_source", "search")
        self.video_urls = settings.get("video_urls", [])
        if isinstance(self.video_urls, str):
            self.video_urls = [u.strip() for u in self.video_urls.split("\n") if u.strip()]

        # Enforce minimum delay for YouTube
        if self.platform == "youtube" and self.delay_seconds < 120:
            self.delay_seconds = 120

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.is_running = True

        mode = "DRY RUN" if self.dry_run else "LIVE"
        topic_label = f"'{self.topic}'" if self.topic else "all content (no filter)"
        if self.platform == "youtube":
            source_label = VIDEO_SOURCE_LABELS.get(self.video_source, self.video_source)
            self.log(f"Bot started in {mode} mode | Platform: YouTube | Source: {source_label} | Topic: {topic_label}")
        else:
            self.log(f"Bot started in {mode} mode | Topic: {topic_label} | Subreddit: r/{self.subreddit}")
        return True

    def stop(self):
        if not self.is_running:
            return False
        self._stop_event.set()
        self.is_running = False
        self.log("Bot stopping...")
        return True

    def _wait(self, seconds):
        """Wait for given seconds, checking stop event every second."""
        for _ in range(seconds):
            if self._stop_event.is_set():
                return False
            time.sleep(1)
        return True

    def _run_loop(self):
        pw = None
        browser = None
        try:
            if self.platform == "youtube":
                pw, browser, page, identity = youtube_create_session()
                self.log(f"Logged into YouTube as {identity}")
            else:
                pw, browser, page, identity = reddit_create_session()
                self.log(f"Logged into Reddit as u/{identity}")
        except Exception as e:
            self.log(f"Login failed: {e}", level="error")
            self.is_running = False
            return

        scan_interval = 600 if self.platform == "youtube" else 300

        try:
            while not self._stop_event.is_set():
                try:
                    self._scan_and_comment(page)
                except Exception as e:
                    self.log(f"Error in scan cycle: {e}", level="error")

                if self._stop_event.is_set():
                    break

                interval_label = f"{scan_interval // 60} minutes"
                self.log(f"Next scan in {interval_label}...")
                if not self._wait(scan_interval):
                    break
        finally:
            if self.platform == "youtube":
                youtube_close_session(pw, browser)
            else:
                reddit_close_session(pw, browser)

        self.log(f"Bot stopped. Total comments: {self.comments_posted}")
        self.is_running = False

    def _scan_and_comment(self, page):
        if self.platform == "youtube":
            self._scan_youtube(page)
        else:
            self._scan_reddit(page)

    def _scan_reddit(self, page):
        self.log(f"Scanning r/{self.subreddit} hot posts...")
        posts = fetch_hot_posts(page, subreddit_name=self.subreddit, limit=50)
        self.log(f"Fetched {len(posts)} posts, classifying...")

        items = []
        for post in posts:
            items.append({
                "id": post["id"],
                "title": post["title"],
                "text": post.get("selftext", ""),
                "source_label": f"r/{post.get('subreddit', '')}",
            })
        self._process_items(page, items)

    def _scan_youtube(self, page):
        source_label = VIDEO_SOURCE_LABELS.get(self.video_source, self.video_source)
        self.log(f"Scanning YouTube ({source_label})...")
        videos = fetch_videos(page, source=self.video_source, topic=self.topic, video_urls=self.video_urls, limit=20)
        self.log(f"Fetched {len(videos)} videos, classifying...")

        items = []
        for video in videos:
            items.append({
                "id": video["id"],
                "title": video["title"],
                "text": video.get("description", ""),
                "source_label": video.get("channel", "YouTube"),
            })
        self._process_items(page, items)

    def _process_items(self, page, items):
        matches = 0
        consecutive_ai_errors = 0
        for item in items:
            if self._stop_event.is_set():
                return

            if item["id"] in self.commented_ids:
                continue

            if self.max_comments > 0 and self.comments_posted >= self.max_comments:
                self.log(f"Reached max comments limit ({self.max_comments}). Stopping.", level="success")
                self._stop_event.set()
                return

            # Classify (skip if no topic — treat everything as a match)
            if self.topic:
                try:
                    is_match = classify_post(item["title"], item["text"], self.topic, platform=self.platform)
                    consecutive_ai_errors = 0
                except Exception as e:
                    consecutive_ai_errors += 1
                    self.log(f"Classification error: {e}", level="error")
                    if consecutive_ai_errors >= 3:
                        self.log("All AI providers unavailable. Waiting 60s before retry...", level="error")
                        if not self._wait(60):
                            return
                        consecutive_ai_errors = 0
                    continue

                if not is_match:
                    continue

            matches += 1
            self.log(f"MATCH: {item['source_label']} - {item['title'][:70]}", level="match")

            # Generate comment
            try:
                comment_text = generate_comment(
                    item["title"],
                    item["text"],
                    self.comment_flavor,
                    self.must_include,
                    self.must_include_context,
                    platform=self.platform,
                )
            except Exception as e:
                self.log(f"Comment generation error: {e}", level="error")
                continue

            # Enforce must-include
            if self.must_include and self.must_include.lower() not in comment_text.lower():
                comment_text += f" {self.must_include}"

            self.log(f"Generated: {comment_text}")

            # Post or dry run
            if self.dry_run:
                self.comments_posted += 1
                self.commented_ids.add(item["id"])
                self.log(
                    f"[DRY RUN] Would post comment #{self.comments_posted} on {item['source_label']}",
                    level="dryrun",
                )
            else:
                try:
                    if self.platform == "youtube":
                        youtube_post_comment(page, item["id"], comment_text)
                    else:
                        reddit_post_comment(page, item["id"], comment_text)
                    self.comments_posted += 1
                    self.commented_ids.add(item["id"])
                    self.log(
                        f"Posted comment #{self.comments_posted} on {item['source_label']}",
                        level="success",
                    )
                except Exception as e:
                    self.log(f"Failed to post comment: {e}", level="error")
                    continue

            # Delay between comments
            actual_delay = self.delay_seconds + random.randint(
                -self.random_offset, self.random_offset
            )
            min_delay = 120 if self.platform == "youtube" else 5
            actual_delay = max(min_delay, actual_delay)
            self.log(f"Waiting {actual_delay}s before next comment...")
            if not self._wait(actual_delay):
                return

        if matches == 0:
            self.log("No matching content found this cycle.")
        else:
            self.log(f"Cycle complete. Found {matches} matches.")
