import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
    REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "redditbot:v1.0")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
