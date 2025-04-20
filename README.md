# 🧠 BrowserLLM API

This API enables **natural language control of a browser** using OpenAI and a headless browser automation system.

---

## 🚀 What It Does

- Accepts **natural language commands** to interact with a browser.
- Uses OpenAI to decide the **next browser action** (click, input, scroll, etc.).
- Automates navigation and interaction with websites.
- Handles multi-turn reasoning with verification (e.g., login, modals, CAPTCHA detection).
- Supports **session-based control** so multiple users/bots can run in parallel.

---

## 📡 API Routes

### `POST /api/browser/interact`
> 🔁 Send a command to the browser for a session.

#### Payload:
```json
{
  "session_id": "your_unique_session_id",
  "command": "go to amazon.com and search for laptops",
  "max_turns": 10,          // optional, default is 10
  "api_key": "sk-...",      // optional, fallback to env
  "driver_path": "/path/to/chromedriver" // optional
}
```

---

### `POST /api/browser/reset`
> ♻️ Reset session & close browser if open.

#### Payload:
```json
{
  "session_id": "your_unique_session_id"
}
```

---

### `POST /api/browser/close`
> ❌ Close the browser (session remains).

#### Payload:
```json
{
  "session_id": "your_unique_session_id"
}
```

---

### `POST /api/browser/cleanup`
> 🧹 Cleanup all or specific sessions.

#### Payload:
```json
{
  "session_ids": ["id1", "id2"] // optional, cleans all if omitted
}
```

---

### `GET /api/browser/status`
> 📊 Get info on all active sessions.

---

## 🧠 How It Works

1. Start a session with `interact` using natural language.
2. OpenAI figures out which browser tool to use.
3. Executes one action at a time, step-by-step.
4. Stops on CAPTCHA or error, resumes on user signal.
5. You can reset, close, or inspect sessions anytime.
