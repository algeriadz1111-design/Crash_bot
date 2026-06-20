# 1xbet Crash Point Tracker — Telegram Bot

Automatically scrapes crash point values from 1xbet and tracks them inside Telegram.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Get a Telegram Bot Token
1. Open Telegram → search for **@BotFather**
2. Send `/newbot` and follow the steps
3. Copy the token you receive

### 3. Set your token
Open `bot.py` and replace:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
```
Or set it as an environment variable:
```bash
export BOT_TOKEN="your_token_here"
```

### 4. Run the bot
```bash
python3 bot.py
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Begin auto-scraping crash points |
| `/stop` | Stop scraping |
| `/history [n]` | Show last N results (default 20, max 100) |
| `/stats` | Min / Max / Average + distribution |
| `/clear` | Wipe all stored data |
| `/help` | List all commands |

---

## How it works

- Uses **Playwright** (headless Chromium) to open the 1xbet crash page
- Listens to **WebSocket frames** the page receives in real-time
- Parses crash multiplier values (`cf`, `x`, or similar keys)
- Stores results in `crash_data.json` (auto-saved after each round)
- Survives restarts — history is reloaded from file on startup

---

## Notes

- 1xbet may block headless browsers or require login. If scraping fails,
  you can switch `bot.py` to manual mode: send crash values as messages
  like `/add 3.45` and the bot will store them.
- The WebSocket payload keys (`cf`, `x`, etc.) may need adjustment
  depending on your region's 1xbet version. Enable `log.setLevel(logging.DEBUG)`
  to inspect raw frames.
- Data is saved to `crash_data.json` in the same directory.
