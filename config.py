import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
    REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "redditbot:v1.0")
    YOUTUBE_USER_AGENT = os.getenv("YOUTUBE_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Mobile emulator mode
    USE_MOBILE = os.getenv("USE_MOBILE", "false").lower() == "true"
    ANDROID_AVD_NAME = os.getenv("ANDROID_AVD_NAME", "redbot_pixel7")
    APPIUM_HOST = os.getenv("APPIUM_HOST", "http://127.0.0.1:4723")
    EMULATOR_PORT = os.getenv("EMULATOR_PORT", "5554")
    YOUTUBE_MOBILE_USER_AGENT = os.getenv(
        "YOUTUBE_MOBILE_USER_AGENT",
        "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    )
