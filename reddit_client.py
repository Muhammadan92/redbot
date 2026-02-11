import praw
from config import Config


def get_reddit_instance():
    """Create an authenticated PRAW Reddit instance."""
    return praw.Reddit(
        client_id=Config.REDDIT_CLIENT_ID,
        client_secret=Config.REDDIT_CLIENT_SECRET,
        username=Config.REDDIT_USERNAME,
        password=Config.REDDIT_PASSWORD,
        user_agent=Config.REDDIT_USER_AGENT,
    )


def fetch_hot_posts(reddit, subreddit_name="all", limit=50):
    """Fetch hot posts from a subreddit. Returns list of post dicts."""
    subreddit = reddit.subreddit(subreddit_name)
    posts = []
    for submission in subreddit.hot(limit=limit):
        if submission.stickied:
            continue
        posts.append({
            "id": submission.id,
            "title": submission.title,
            "selftext": submission.selftext[:500],
            "url": submission.url,
            "subreddit": str(submission.subreddit),
            "num_comments": submission.num_comments,
            "permalink": submission.permalink,
        })
    return posts


def post_comment(reddit, submission_id, comment_text):
    """Post a comment on a Reddit submission."""
    submission = reddit.submission(id=submission_id)
    return submission.reply(comment_text)
