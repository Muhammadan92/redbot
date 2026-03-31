# RedBot - YouTube & Reddit Comment Bot

This bot scans YouTube videos and Reddit posts matching topics you specify, uses AI to generate relevant comments, and posts them automatically. It comes with a web control panel for configuration and live monitoring.

> **VPN Recommended:** We strongly recommend using a VPN at all times when running this bot. Both YouTube and Reddit can flag or throttle accounts based on IP patterns. A VPN adds a layer of protection for your account and helps avoid detection. Rotate your VPN location periodically for best results.

---

# YouTube Bot

## What It Does

- Finds recent YouTube videos by **search**, **trending**, or **specific URLs**
- Uses AI to classify which videos match your topic
- Generates natural-sounding comments with your desired tone
- Simulates human behavior (watching, scrolling, gradual typing) to reduce detection
- Supports dry-run mode to preview without posting
- Live activity log in the browser

## Prerequisites

- **Python 3.10+**
- **Google Chrome browser** (required for YouTube login session)
- **A Google/YouTube account** (you'll log in manually once)
- **A Groq API key** (free, no credit card)
- **A Google Gemini API key** (free, used as fallback)
- **An OpenAI API key** (optional, paid fallback - very cheap, ~$0.58/day at max usage)

> **Note:** YouTube does not require any YouTube API key. The bot uses browser automation to interact with YouTube directly.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

> **Note:** The bot uses your system-installed Google Chrome (not Playwright's bundled Chromium). Make sure Chrome is installed on your machine.

### 2. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and fill in your AI API keys (at least one required):

```
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_key_here
OPENAI_API_KEY=sk-your_openai_key_here
```

### 3. Get Your AI API Keys

#### Groq (Primary AI - Free)

1. Go to https://console.groq.com
2. Sign up with Google, GitHub, or email
3. Click **API Keys** in the left sidebar
4. Click **Create API Key**, name it anything (e.g. "redbot")
5. Copy the key immediately (starts with `gsk_`) - it won't be shown again
6. Paste it as `GROQ_API_KEY` in your `.env` file

#### Google Gemini (Fallback AI - Free)

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **Create API Key**
4. Select or create a Google Cloud project (no billing required)
5. Copy the key (starts with `AIzaSy`)
6. Paste it as `GEMINI_API_KEY` in your `.env` file

#### OpenAI (Paid Fallback - Very Cheap)

1. Go to https://platform.openai.com/api-keys
2. Sign up or sign in
3. Add a payment method (Settings > Billing) - pay-as-you-go, no minimum
4. Click **Create new secret key**, name it anything
5. Copy the key (starts with `sk-`)
6. Paste it as `OPENAI_API_KEY` in your `.env` file

Uses GPT-4.1-nano (~$0.10 per million input tokens). At heavy usage this costs under $1/day.

The bot tries free providers first: **Groq -> Gemini -> OpenAI** (paid, only used if both free options fail).

### 4. Save Your YouTube Session (One-Time)

```bash
python save_youtube_session.py
```

This opens a **real Chrome window**. Follow the steps:

1. Log into your Google account in the Chrome window
2. Complete any 2FA or verification if prompted
3. Make sure you can see YouTube and are logged in
4. Go back to the terminal and press **Enter**

Your session is saved to `youtube_session.json`. A `.chrome-profile-youtube/` directory is also created to store persistent browser data.

**When to re-run this:** If you see a "session expired" error or your comments stop posting, just run `python save_youtube_session.py` again.

## Running the Bot

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser and click the **YouTube** toggle at the top.

## Control Panel Settings

### Video Source

Choose how the bot finds videos to comment on:

| Source | Description |
|--------|-------------|
| **Search by topic** | Searches YouTube for videos uploaded in the last hour matching your topic. Best for finding fresh content. |
| **Trending** | Scans the YouTube trending page. Good for high-visibility commenting. |
| **Paste URLs** | Comment on specific videos you provide. Enter one URL per line. Supports `youtube.com/watch?v=`, `youtu.be/`, `/shorts/`, and `/live/` formats. |

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Topic to scan for** | What kind of videos to look for (e.g. "artificial intelligence", "gaming news"). Required for Search mode. You can enter multiple topics separated by commas (e.g. "python, javascript, golang") and the bot will match videos relevant to **any** of them. | *Required for Search* |
| **Comment flavor / tone** | How the comment should sound (e.g. "friendly and enthusiastic", "insightful", "casual") | *Required* |
| **Comment MUST have** | Text that must appear in every comment, such as a product name or URL (optional) | Empty |
| **How to mention it** | Context for how the required text should be worked in (e.g. "as a helpful resource", "as a personal recommendation") | Empty |
| **Max comments** | Stop after this many comments. Check "Unlimited" to keep going. | 10 |
| **Delay (seconds)** | Wait time between comments. **Minimum 120 seconds is auto-enforced for YouTube** to reduce detection risk. | 120 |
| **Random offset** | Adds randomness to delay (+/- this many seconds) | 10 |
| **Dry Run** | When checked, the bot finds and classifies videos and generates comments but does NOT post them. **Always test with this on first.** | Checked |

## How It Works

1. **Fetch**: The bot finds videos based on your chosen source (search/trending/URLs), loading up to 20 videos per cycle
2. **Classify**: Each video's title and description are sent to the AI, which decides if it matches your topic (yes/no)
3. **Generate**: For matching videos, the AI writes a natural comment using your specified tone
4. **Simulate**: The bot navigates to the video, waits 8-20 seconds (simulating watching), and scrolls gradually to the comments section
5. **Type & Post**: The comment is typed character-by-character with human-like delays (30-80ms per character), then submitted (or just logged in dry-run mode)
6. **Wait**: The bot waits for the configured delay (minimum 120 seconds + random offset) before the next comment
7. **Repeat**: After processing all videos, it waits **10 minutes** and scans again

The activity log shows every step in real time.

## YouTube Tips

- **Always start with Dry Run enabled** to verify the bot is finding and classifying the right videos
- **Use a VPN** to protect your account and reduce the risk of flagging
- **Keep delays high** - the 120-second minimum is enforced, but longer delays (180-300s) are safer for long sessions
- **Multiple topics** - enter comma-separated topics to cast a wider net (e.g. "tech news, AI, startups" matches videos about any of those)
- **Paste URLs mode** is useful for targeting specific videos where you want to leave a comment
- The bot uses a separate Chrome profile and session from Reddit, so you can switch between platforms without conflict

## YouTube Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No saved YouTube session found"** | Run `python save_youtube_session.py` to log in and save your session |
| **"YouTube session expired"** | Run `python save_youtube_session.py` again to refresh your session |
| **"Comments are disabled on this video"** | The video has comments turned off. The bot will skip it and move on |
| **"Classification error"** | Check your AI API keys in `.env`. Make sure at least one of GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY is valid |
| **No matching videos found** | Try broadening your topic, use comma-separated topics, or switch to Trending mode |
| **Comments not appearing on YouTube** | YouTube may be silently filtering your comments. Try using a VPN, varying your comment tone, or reducing frequency |
| **Bot seems slow** | YouTube mode intentionally runs slower (120s+ delays, 10-min scan cycles) to mimic human behavior |

---

# Reddit Bot

## What It Does

- Scans hot posts from any subreddit (or all of Reddit)
- Uses AI to classify which posts match your topic
- Generates natural-sounding comments with your desired tone
- Can require specific text in every comment (e.g. a product name, link, etc.)
- Supports dry-run mode to preview without posting
- Live activity log in the browser

> **Shadowban Warning:** Reddit is very aggressive about detecting and shadowbanning bot accounts. A shadowban means your comments are silently hidden from everyone except you - you won't get any error, but nobody else can see your posts. This is difficult to avoid entirely. To minimize risk: use a VPN, keep delays high, vary your comment tone, avoid posting too frequently, and use aged accounts rather than new ones. Check your account status periodically by viewing your profile in an incognito/private browser window.

## Additional Prerequisites

Everything from the YouTube setup above (Python, Chrome, AI API keys) is shared. You additionally need:

- **A Reddit account** (username and password)

## Setup

### 1. Add Reddit Credentials to `.env`

Add these lines to your `.env` file (created during YouTube setup, or run `cp .env.example .env` if you haven't):

```
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36
```

### 2. Save Your Reddit Session (One-Time)

```bash
python save_session.py
```

This opens a **real Chrome window** (not Playwright's built-in browser) to avoid Reddit's bot detection. Follow the steps:

1. Log into Reddit in the Chrome window
2. Complete any CAPTCHA or 2FA if prompted
3. Wait until you see your Reddit homepage
4. Go back to the terminal and press **Enter**

Your session is saved to `reddit_session.json`. A `.chrome-profile/` directory is also created to store persistent browser data.

**When to re-run this:** If you see a "session expired" error, just run `python save_session.py` again. The persistent Chrome profile is reused automatically.

## Running the Bot

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser. Reddit mode is selected by default.

## Control Panel Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Subreddit to scan** | Which subreddit to scan (e.g. `technology`, `gaming`). Use `all` for the front page. | `all` |
| **Topic to scan for** | What kind of posts to look for (e.g. "artificial intelligence", "electric vehicles"). Comma-separated topics match **any** of them. Leave blank to match all posts. | Optional |
| **Comment flavor / tone** | How the comment should sound (e.g. "friendly and helpful", "witty", "professional") | *Required* |
| **Comment MUST have** | Text that must appear in every comment, such as a product name or URL (optional) | Empty |
| **How to mention it** | Context for how the required text should be worked in (e.g. "as a helpful resource", "as a personal recommendation") | Empty |
| **Max comments** | Stop after this many comments. Check "Unlimited" to keep going. | 10 |
| **Delay (seconds)** | Base wait time between comments | 30 |
| **Random offset** | Adds randomness to delay (+/- this many seconds) | 10 |
| **Dry Run** | When checked, the bot classifies posts and generates comments but does NOT actually post them. Always test with this on first. | Checked |

## How It Works

1. **Scan**: The bot fetches the 50 hottest posts from your chosen subreddit via Reddit's JSON endpoint (using your saved session)
2. **Classify**: Each post is sent to the AI, which decides if it matches your topic (yes/no)
3. **Generate**: For matching posts, the AI writes a natural comment using your specified tone
4. **Post**: The comment is posted via the browser session (or just logged in dry-run mode)
5. **Wait**: The bot waits for the configured delay (with random offset) before the next comment
6. **Repeat**: After processing all posts, it waits 5 minutes and scans again

## Reddit Troubleshooting

| Problem | Solution |
|---------|----------|
| **"No saved Reddit session found"** | Run `python save_session.py` to log in and save your session |
| **"Saved session expired"** | Run `python save_session.py` again to refresh your session |
| **"Reddit login failed"** | Check your username/password in `.env`, then re-run `save_session.py` |
| **"Classification error" or "Comment generation error"** | Check your API keys in `.env`. Make sure at least one of GROQ_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY is valid |
| **"Failed to post comment"** | Your session may have expired, or the post may be locked/archived. Re-run `save_session.py` |
| **No matching posts found** | Try broadening your topic, or scan a more specific subreddit |
| **Bot stops after a few comments** | Check your "Max comments" setting. Uncheck "Unlimited" if you want no limit |
| **403 Blocked on scan** | Your user agent looks like a bot. Update `REDDIT_USER_AGENT` in `.env` to a Chrome browser user agent string |
| **Comments not visible to others** | You may be shadowbanned. Check your profile in an incognito window. Consider using a VPN and a different account. |
| **`playwright install` fails** | Make sure you have a stable internet connection. On Linux you may need `sudo playwright install-deps` first |

---

# Project Structure

```
redbot/
  app.py                    - Flask web server (start here)
  bot.py                    - Bot engine (scanning, posting logic)
  ai_client.py              - AI integration (Groq + Gemini + OpenAI)
  reddit_client.py          - Reddit session & comment posting
  youtube_client.py         - YouTube session, video fetching & comment posting
  config.py                 - Environment variable loader
  save_session.py           - One-time Reddit login script
  save_youtube_session.py   - One-time YouTube/Google login script
  requirements.txt          - Python dependencies
  .env.example              - Environment variable template
  .gitignore                - Git ignore rules
  .chrome-profile/          - Persistent Chrome browser data for Reddit (auto-created)
  .chrome-profile-youtube/  - Persistent Chrome browser data for YouTube (auto-created)
  templates/
    index.html              - Control panel HTML
  static/
    style.css               - Dark theme styles
    app.js                  - Frontend JavaScript
```
