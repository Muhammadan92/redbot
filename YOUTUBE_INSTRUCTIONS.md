# Running the YouTube Comment Bot

## Prerequisites

Make sure you have Python 3 and the required dependencies installed:

```bash
pip install playwright flask python-dotenv groq openai google-generativeai
playwright install chromium
```

Set up at least one AI API key in your `.env` file (Groq is free):

```
GROQ_API_KEY=your_key_here
```

## Step 1: Save Your YouTube Session

```bash
python save_youtube_session.py
```

This opens a Chrome window. Log into your Google account, complete any 2FA, then press ENTER in the terminal. Your session is saved to `youtube_session.json`.

## Step 2: Start the Bot

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Step 3: Configure

1. Click the **YouTube** toggle button at the top
2. Choose a video source:
   - **Search by topic** — finds recent videos matching your topic
   - **Trending** — scans the trending page
   - **Paste URLs** — comment on specific videos
3. Enter a **Topic** (used for both finding and classifying videos)
4. Enter a **Comment flavor/tone** (e.g. "friendly and enthusiastic")
5. Optionally set **Must have** text and **How to mention it**
6. Delay is auto-set to **120s minimum** for YouTube
7. **Enable Dry Run first** to test without actually posting

## Step 4: Run

Click **START** and watch the Activity Log for:
- Video fetching
- AI classification matches
- Generated comments
- Posted (or dry-run) confirmations

Once satisfied with dry run results, uncheck Dry Run and restart for live commenting.

## Notes

- YouTube is stricter than Reddit — the bot enforces **120s minimum** between comments and uses **10-minute scan cycles**
- The bot simulates watching (8-20s random wait + scrolling) before commenting to reduce detection
- To switch back to Reddit, just click the **Reddit** toggle — your Reddit session is separate
- If your YouTube session expires, re-run `python save_youtube_session.py`
