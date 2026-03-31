const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");
const commentCount = document.getElementById("comment-count");
const activityLog = document.getElementById("activity-log");
const unlimitedCheckbox = document.getElementById("unlimited");
const maxCommentsInput = document.getElementById("max-comments");
const delayInput = document.getElementById("delay");

let currentPlatform = "reddit";

// Platform toggle
document.querySelectorAll(".platform-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".platform-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentPlatform = btn.dataset.platform;

        document.getElementById("reddit-settings").style.display =
            currentPlatform === "reddit" ? "block" : "none";
        document.getElementById("youtube-settings").style.display =
            currentPlatform === "youtube" ? "block" : "none";

        // Enforce minimum delay for YouTube
        if (currentPlatform === "youtube") {
            delayInput.min = 120;
            if (parseInt(delayInput.value) < 120) {
                delayInput.value = 120;
            }
        } else {
            delayInput.min = 5;
        }
    });
});

// Video source radio toggle
document.querySelectorAll('input[name="video-source"]').forEach((radio) => {
    radio.addEventListener("change", () => {
        document.getElementById("video-urls-group").style.display =
            radio.value === "urls" && radio.checked ? "block" : "none";
    });
});

// Toggle max comments input when unlimited is checked
unlimitedCheckbox.addEventListener("change", () => {
    maxCommentsInput.disabled = unlimitedCheckbox.checked;
    if (unlimitedCheckbox.checked) {
        maxCommentsInput.style.opacity = "0.4";
    } else {
        maxCommentsInput.style.opacity = "1";
    }
});

// SSE connection for live logs
let evtSource = null;

function connectSSE() {
    if (evtSource) evtSource.close();
    evtSource = new EventSource("/stream");
    evtSource.addEventListener("log", (e) => {
        const data = JSON.parse(e.data);
        appendLog(data.time, data.level, data.message);
    });
    evtSource.onerror = () => {
        // Reconnect after a brief delay
        setTimeout(connectSSE, 3000);
    };
}

function appendLog(time, level, message) {
    const entry = document.createElement("div");
    entry.className = `log-entry log-${level}`;
    entry.textContent = `[${time}] ${message}`;
    activityLog.appendChild(entry);
    activityLog.scrollTop = activityLog.scrollHeight;
}

// Start bot
startBtn.addEventListener("click", async () => {
    const topic = document.getElementById("topic").value.trim();
    const flavor = document.getElementById("flavor").value.trim();

    if (!topic && currentPlatform === "youtube") {
        const videoSource = document.querySelector('input[name="video-source"]:checked').value;
        if (videoSource === "search") {
            alert("Topic is required for YouTube search mode.");
            return;
        }
    }
    if (!flavor) {
        alert("Please enter a comment flavor/tone.");
        return;
    }

    const settings = {
        platform: currentPlatform,
        topic: topic,
        comment_flavor: flavor,
        must_include: document.getElementById("must-include").value.trim(),
        must_include_context: document.getElementById("must-include-context").value.trim(),
        max_comments: unlimitedCheckbox.checked
            ? 0
            : parseInt(maxCommentsInput.value) || 10,
        delay_seconds: parseInt(delayInput.value) || 30,
        random_offset: parseInt(document.getElementById("offset").value) || 10,
        dry_run: document.getElementById("dry-run").checked,
    };

    if (currentPlatform === "reddit") {
        settings.subreddit = document.getElementById("subreddit").value.trim();
    } else {
        const videoSource = document.querySelector('input[name="video-source"]:checked').value;
        settings.video_source = videoSource;
        if (videoSource === "urls") {
            settings.video_urls = document.getElementById("video-urls").value.trim();
        }
    }

    try {
        const res = await fetch("/api/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings),
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error);
            return;
        }
        setRunningState(true);
    } catch (err) {
        alert("Failed to start bot: " + err.message);
    }
});

// Stop bot
stopBtn.addEventListener("click", async () => {
    try {
        const res = await fetch("/api/stop", { method: "POST" });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error);
            return;
        }
        setRunningState(false);
    } catch (err) {
        alert("Failed to stop bot: " + err.message);
    }
});

function setRunningState(running) {
    startBtn.disabled = running;
    stopBtn.disabled = !running;
    statusDot.className = running ? "status-dot running" : "status-dot stopped";
    statusText.textContent = running ? "Running" : "Stopped";

    // Disable inputs while running
    const inputs = document.querySelectorAll(".settings input, .settings textarea");
    inputs.forEach((input) => {
        if (input.id !== "unlimited" || !running) {
            input.disabled = running;
        }
    });

    // Disable platform toggle while running
    document.querySelectorAll(".platform-btn").forEach((btn) => {
        btn.disabled = running;
    });
}

// Poll status every 3 seconds
async function updateStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        commentCount.textContent = data.comments_posted;
        setRunningState(data.is_running);
    } catch {
        // Server might be down, ignore
    }
}

setInterval(updateStatus, 3000);

// Initialize
connectSSE();
updateStatus();
