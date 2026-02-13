# Reddit Bot - Setup & Usage Instructions

## What This Bot Does

This bot scans Reddit for posts matching a topic you specify, uses AI to generate relevant comments, and posts them automatically. It comes with a web control panel for configuration and live monitoring.

- Scans hot posts from any subreddit (or all of Reddit)
- Uses AI to classify which posts match your topic
- Generates natural-sounding comments with your desired tone
- Can require specific text in every comment (e.g. a product name, link, etc.)
- Supports dry-run mode to preview without posting
- Live activity log in the browser

---

## Prerequisites

- **Python 3.10+**
- **Google Chrome browser** (required for Reddit login session)
- **A Reddit account** (username and password)
- **A Groq API key** (free, no credit card)
- **A Google Gemini API key** (free, used as fallback)
- **An OpenAI API key** (optional, paid fallback - very cheap, ~$0.58/day at max usage)

---

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

Edit `.env` and fill in these values:

```
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36

GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIzaSy_your_gemini_key_here
OPENAI_API_KEY=sk-your_openai_key_here
```

### 3. Get Your AI API Keys

#### Groq (Primary AI - Free)

1. Go to https://console.groq.com
2. Sign up with Google, GitHub, or email
3. Click **API Keys** in the left sidebar
4. Click **Create API Key**, name it anything (e.g. "redditbot")
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

### 4. Save Your Reddit Session (One-Time)

Reddit blocks automated logins, so you need to log in manually once:

```bash
python save_session.py
```

This opens a **real Chrome window** (not Playwright's built-in browser) to avoid Reddit's bot detection. Follow the steps:

1. Log into Reddit in the Chrome window
2. Complete any CAPTCHA or 2FA if prompted
3. Wait until you see your Reddit homepage
4. Go back to the terminal and press **Enter**

Your session is saved to `reddit_session.json`. A `.chrome-profile/` directory is also created to store persistent browser data, which helps avoid future bot detection.

**When to re-run this:** If you see a "session expired" error, just run `python save_session.py` again. The persistent Chrome profile is reused automatically.

---

## Running the Bot

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser to access the control panel.

---

## Control Panel Settings

| Setting | Description | Default |
|---------|-------------|---------|
| **Subreddit to scan** | Which subreddit to scan (e.g. `technology`, `gaming`). Use `all` for the front page. | `all` |
| **Topic to scan for** | What kind of posts to look for (e.g. "artificial intelligence", "electric vehicles") | *Required* |
| **Comment flavor / tone** | How the comment should sound (e.g. "friendly and helpful", "witty", "professional") | *Required* |
| **Comment MUST have** | Text that must appear in every comment, such as a product name or URL (optional) | Empty |
| **How to mention it** | Context for how the required text should be worked in (e.g. "as a helpful resource", "as a personal recommendation") | Empty |
| **Max comments** | Stop after this many comments. Check "Unlimited" to keep going. | 10 |
| **Delay (seconds)** | Base wait time between comments | 30 |
| **Random offset** | Adds randomness to delay (+/- this many seconds) | 10 |
| **Dry Run** | When checked, the bot classifies posts and generates comments but does NOT actually post them. Always test with this on first. | Checked |

---

## How It Works

1. **Scan**: The bot fetches the 50 hottest posts from your chosen subreddit using Reddit's public JSON API
2. **Classify**: Each post is sent to the AI, which decides if it matches your topic (yes/no)
3. **Generate**: For matching posts, the AI writes a natural comment using your specified tone
4. **Post**: The comment is posted via the browser session (or just logged in dry-run mode)
5. **Wait**: The bot waits for the configured delay (with random offset) before the next comment
6. **Repeat**: After processing all posts, it waits 5 minutes and scans again

The activity log shows every step in real time.

---

## Troubleshooting

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
| **401 Unauthorized on save_session.py** | Reddit is blocking the automated browser. Make sure Google Chrome is installed on your system |
| **`playwright install` fails** | Make sure you have a stable internet connection. On Linux you may need `sudo playwright install-deps` first |

---

## Project Structure

```
redditBot/
  app.py              - Flask web server (start here)
  bot.py              - Bot engine (scanning, posting logic)
  ai_client.py        - AI integration (Groq + Gemini + OpenAI)
  reddit_client.py    - Reddit session & comment posting
  config.py           - Environment variable loader
  save_session.py     - One-time Reddit login script
  requirements.txt    - Python dependencies
  .env.example        - Environment variable template
  .gitignore          - Git ignore rules
  .chrome-profile/    - Persistent Chrome browser data (auto-created)
  templates/
    index.html        - Control panel HTML
  static/
    style.css         - Dark theme styles
    app.js            - Frontend JavaScript
```
