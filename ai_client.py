from groq import Groq
import google.generativeai as genai
from config import Config

groq_client = None
gemini_model = None


def _init_groq():
    global groq_client
    if groq_client is None and Config.GROQ_API_KEY:
        groq_client = Groq(api_key=Config.GROQ_API_KEY)
    return groq_client


def _init_gemini():
    global gemini_model
    if gemini_model is None and Config.GEMINI_API_KEY:
        genai.configure(api_key=Config.GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite")
    return gemini_model


def call_ai(system_prompt, user_prompt):
    """Call Groq first. If it fails, fall back to Gemini. Raises RuntimeError if both fail."""
    errors = []

    client = _init_groq()
    if client:
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            errors.append(f"Groq: {e}")

    model = _init_gemini()
    if model:
        try:
            combined = f"{system_prompt}\n\n{user_prompt}"
            response = model.generate_content(combined)
            return response.text.strip()
        except Exception as e:
            errors.append(f"Gemini: {e}")

    raise RuntimeError(f"All AI providers failed: {'; '.join(errors)}")


def classify_post(post_title, post_text, target_topic):
    """Ask AI if a post matches the target topic. Returns True/False."""
    system_prompt = (
        "You are a content classifier. You will receive a Reddit post title and text. "
        "Determine if it is relevant to the given topic. "
        "Respond with ONLY 'yes' or 'no'. Nothing else."
    )
    user_prompt = (
        f"Topic to match: {target_topic}\n\n"
        f"Post title: {post_title}\n"
        f"Post text: {post_text[:300]}"
    )
    result = call_ai(system_prompt, user_prompt)
    return result.lower().strip().startswith("yes")


def generate_comment(post_title, post_text, comment_flavor, must_include):
    """Generate a Reddit comment for the given post."""
    must_include_instruction = ""
    if must_include:
        must_include_instruction = (
            f"The comment MUST naturally include the following: '{must_include}'. "
        )

    system_prompt = (
        f"You are a Reddit commenter. Write a natural, human-sounding comment. "
        f"Style/tone: {comment_flavor}. "
        f"{must_include_instruction}"
        f"Keep the comment between 1-3 sentences. Do not use quotation marks around the whole response. "
        f"Do not start with 'As an AI' or similar disclaimers."
    )
    user_prompt = (
        f"Write a Reddit comment for this post:\n"
        f"Title: {post_title}\n"
        f"Content: {post_text[:300]}"
    )
    return call_ai(system_prompt, user_prompt)
