from flask import Flask, render_template, request, jsonify, Response
from bot import MessageAnnouncer, BotEngine
from config import Config

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

announcer = MessageAnnouncer()
bot = BotEngine(announcer)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/start", methods=["POST"])
def api_start():
    data = request.get_json()
    if not data.get("comment_flavor"):
        return jsonify({"error": "Comment flavor is required"}), 400

    platform = data.get("platform", "reddit")
    if platform == "youtube":
        source = data.get("video_source", "search")
        if source == "search" and not data.get("topic"):
            return jsonify({"error": "Topic is required for YouTube search mode"}), 400
        if source == "urls":
            urls = data.get("video_urls", "")
            if isinstance(urls, str):
                urls = [u.strip() for u in urls.split("\n") if u.strip()]
            if not urls:
                return jsonify({"error": "At least one video URL is required"}), 400

    success = bot.start(data)
    if success:
        return jsonify({"status": "started"})
    return jsonify({"error": "Bot is already running"}), 409


@app.route("/api/stop", methods=["POST"])
def api_stop():
    success = bot.stop()
    if success:
        return jsonify({"status": "stopping"})
    return jsonify({"error": "Bot is not running"}), 409


@app.route("/api/status")
def api_status():
    return jsonify({
        "is_running": bot.is_running,
        "comments_posted": bot.comments_posted,
        "topic": bot.topic,
        "dry_run": bot.dry_run,
        "platform": bot.platform,
    })


@app.route("/stream")
def stream():
    def event_stream():
        q = announcer.listen()
        while True:
            msg = q.get()
            yield msg

    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000, threaded=True)
