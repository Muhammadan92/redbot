import httpx
from config import Config

BASE_HEADERS = {
    "User-Agent": Config.REDDIT_USER_AGENT,
}


def create_session():
    """Log into Reddit via old.reddit.com and return (session, modhash)."""
    session = httpx.Client(
        headers=BASE_HEADERS,
        follow_redirects=True,
        timeout=30.0,
    )

    resp = session.post(
        "https://old.reddit.com/api/login",
        data={
            "user": Config.REDDIT_USERNAME,
            "passwd": Config.REDDIT_PASSWORD,
            "api_type": "json",
        },
    )
    resp.raise_for_status()

    result = resp.json()
    errors = result.get("json", {}).get("errors", [])
    if errors:
        raise RuntimeError(f"Reddit login failed: {errors}")

    modhash = result["json"]["data"]["modhash"]
    return session, modhash


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


def post_comment(session, modhash, submission_id, comment_text):
    """Post a comment on a Reddit submission using session auth."""
    resp = session.post(
        "https://old.reddit.com/api/comment",
        data={
            "thing_id": f"t3_{submission_id}",
            "text": comment_text,
            "uh": modhash,
            "api_type": "json",
        },
    )
    resp.raise_for_status()

    result = resp.json()
    errors = result.get("json", {}).get("errors", [])
    if errors:
        raise RuntimeError(f"Comment failed: {errors}")

    return result
