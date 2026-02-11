import threading
import time
import random
import json
import queue
from datetime import datetime
from reddit_client import get_reddit_instance, fetch_hot_posts, post_comment
from ai_client import classify_post, generate_comment


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

        self.topic = ""
        self.subreddit = "all"
        self.comment_flavor = ""
        self.must_include = ""
        self.max_comments = 0  # 0 = unlimited
        self.delay_seconds = 30
        self.random_offset = 10
        self.dry_run = False
        self.comments_posted = 0
        self.commented_posts = set()

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

        self.topic = settings["topic"]
        self.subreddit = settings.get("subreddit", "all").strip() or "all"
        self.comment_flavor = settings["comment_flavor"]
        self.must_include = settings.get("must_include", "")
        self.max_comments = int(settings.get("max_comments", 0))
        self.delay_seconds = int(settings.get("delay_seconds", 30))
        self.random_offset = int(settings.get("random_offset", 10))
        self.dry_run = settings.get("dry_run", False)
        self.comments_posted = 0
        self.commented_posts = set()

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.is_running = True

        mode = "DRY RUN" if self.dry_run else "LIVE"
        self.log(f"Bot started in {mode} mode | Topic: '{self.topic}' | Subreddit: r/{self.subreddit}")
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
        try:
            reddit = get_reddit_instance()
            self.log("Connected to Reddit as u/" + str(reddit.user.me()))
        except Exception as e:
            self.log(f"Reddit connection failed: {e}", level="error")
            self.is_running = False
            return

        while not self._stop_event.is_set():
            try:
                self._scan_and_comment(reddit)
            except Exception as e:
                self.log(f"Error in scan cycle: {e}", level="error")

            # Check if we hit max comments and stopped
            if self._stop_event.is_set():
                break

            self.log("Next scan in 5 minutes...")
            if not self._wait(300):
                break

        self.log(f"Bot stopped. Total comments: {self.comments_posted}")
        self.is_running = False

    def _scan_and_comment(self, reddit):
        self.log(f"Scanning r/{self.subreddit} hot posts...")
        posts = fetch_hot_posts(reddit, subreddit_name=self.subreddit, limit=50)
        self.log(f"Fetched {len(posts)} posts, classifying...")

        matches = 0
        for post in posts:
            if self._stop_event.is_set():
                return

            if post["id"] in self.commented_posts:
                continue

            if self.max_comments > 0 and self.comments_posted >= self.max_comments:
                self.log(f"Reached max comments limit ({self.max_comments}). Stopping.", level="success")
                self._stop_event.set()
                return

            # Classify
            try:
                is_match = classify_post(post["title"], post["selftext"], self.topic)
            except Exception as e:
                self.log(f"Classification error: {e}", level="error")
                continue

            if not is_match:
                continue

            matches += 1
            self.log(f"MATCH: r/{post['subreddit']} - {post['title'][:70]}", level="match")

            # Generate comment
            try:
                comment_text = generate_comment(
                    post["title"],
                    post["selftext"],
                    self.comment_flavor,
                    self.must_include,
                )
            except Exception as e:
                self.log(f"Comment generation error: {e}", level="error")
                continue

            # Enforce must-include
            if self.must_include and self.must_include.lower() not in comment_text.lower():
                comment_text += f" {self.must_include}"

            self.log(f"Generated: {comment_text[:100]}...")

            # Post or dry run
            if self.dry_run:
                self.comments_posted += 1
                self.commented_posts.add(post["id"])
                self.log(
                    f"[DRY RUN] Would post comment #{self.comments_posted} on r/{post['subreddit']}",
                    level="dryrun",
                )
            else:
                try:
                    post_comment(reddit, post["id"], comment_text)
                    self.comments_posted += 1
                    self.commented_posts.add(post["id"])
                    self.log(
                        f"Posted comment #{self.comments_posted} on r/{post['subreddit']}",
                        level="success",
                    )
                except Exception as e:
                    self.log(f"Failed to post comment: {e}", level="error")
                    continue

            # Delay between comments
            actual_delay = self.delay_seconds + random.randint(
                -self.random_offset, self.random_offset
            )
            actual_delay = max(5, actual_delay)
            self.log(f"Waiting {actual_delay}s before next comment...")
            if not self._wait(actual_delay):
                return

        if matches == 0:
            self.log("No matching posts found this cycle.")
        else:
            self.log(f"Cycle complete. Found {matches} matches.")
