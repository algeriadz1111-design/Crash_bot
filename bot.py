"""
1xbet Crash Point Tracker - Telegram Bot
Scrapes crash values via WebSocket/Playwright and stores them.
"""

import asyncio
import json
import os
import logging
from datetime import datetime
from collections import deque

from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ── Config ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DATA_FILE = "crash_data.json"
MAX_HISTORY = 1000          # max results kept in memory
XBET_CRASH_URL = "https://1xbet.com/en/casino/game/crash"   # adjust if needed

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── In-memory store ──────────────────────────────────────────────────────────
crash_history: deque = deque(maxlen=MAX_HISTORY)
scraper_task: asyncio.Task | None = None
scraper_running = False


# ── Persistence ──────────────────────────────────────────────────────────────
def load_data():
    """Load saved crash points from JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                crash_history.extend(data.get("history", []))
                log.info(f"Loaded {len(crash_history)} saved results.")
        except Exception as e:
            log.warning(f"Could not load data: {e}")


def save_data():
    """Persist crash points to JSON file."""
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"history": list(crash_history)}, f, indent=2)
    except Exception as e:
        log.warning(f"Could not save data: {e}")


# ── Scraper ──────────────────────────────────────────────────────────────────
async def scrape_crash_points(app):
    """
    Uses Playwright to open 1xbet crash page and listen to WebSocket
    messages for crash multiplier values.
    """
    global scraper_running
    log.info("Starting Playwright scraper...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # Listen for WebSocket frames that contain crash data
        def handle_ws(ws):
            async def on_frame(payload):
                try:
                    text = payload if isinstance(payload, str) else payload.decode("utf-8", errors="ignore")
                    # 1xbet sends JSON frames; crash value appears as "cf" or "x"
                    if not text.startswith("{"):
                        return
                    msg = json.loads(text)

                    # Adjust these keys based on actual WS payload structure
                    crash_value = (
                        msg.get("cf")          # common key in some versions
                        or msg.get("x")
                        or msg.get("crash_point")
                        or msg.get("multiplier")
                    )
                    if crash_value is not None:
                        val = float(crash_value)
                        entry = {
                            "value": val,
                            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        }
                        crash_history.append(entry)
                        save_data()
                        log.info(f"💥 Crash point captured: {val}x")
                except Exception:
                    pass   # ignore non-crash frames

            ws.on("framereceived", lambda p: asyncio.ensure_future(on_frame(p)))

        page.on("websocket", handle_ws)

        try:
            await page.goto(XBET_CRASH_URL, timeout=60000)
            log.info("Page loaded. Listening for crash events...")

            while scraper_running:
                await asyncio.sleep(1)

        except Exception as e:
            log.error(f"Scraper error: {e}")
        finally:
            await browser.close()
            log.info("Scraper stopped.")


# ── Bot command handlers ──────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Start the scraper."""
    global scraper_task, scraper_running

    if scraper_running:
        await update.message.reply_text("⚡ Scraper is already running!")
        return

    scraper_running = True
    scraper_task = asyncio.create_task(scrape_crash_points(ctx.application))
    await update.message.reply_text(
        "✅ *Crash tracker started!*\n\n"
        "Commands:\n"
        "/history — last results\n"
        "/stats — min / max / avg\n"
        "/stop — stop tracking",
        parse_mode="Markdown",
    )


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Stop the scraper."""
    global scraper_task, scraper_running

    if not scraper_running:
        await update.message.reply_text("ℹ️ Scraper is not running.")
        return

    scraper_running = False
    if scraper_task:
        scraper_task.cancel()
        scraper_task = None

    await update.message.reply_text("🛑 Scraper stopped.")


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show last N crash results."""
    args = ctx.args
    n = 20
    if args:
        try:
            n = max(1, min(int(args[0]), 100))
        except ValueError:
            pass

    if not crash_history:
        await update.message.reply_text("📭 No crash data yet. Use /start to begin tracking.")
        return

    items = list(crash_history)[-n:]
    lines = [f"`{e['value']:.2f}x`  —  {e['time']}" for e in reversed(items)]
    text = f"📋 *Last {len(items)} crash points:*\n\n" + "\n".join(lines)
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show statistics."""
    if not crash_history:
        await update.message.reply_text("📭 No data yet. Use /start to begin tracking.")
        return

    values = [e["value"] for e in crash_history]
    total = len(values)
    avg = sum(values) / total
    mn = min(values)
    mx = max(values)

    # Buckets
    under2 = sum(1 for v in values if v < 2)
    between2_10 = sum(1 for v in values if 2 <= v < 10)
    over10 = sum(1 for v in values if v >= 10)

    text = (
        f"📊 *Crash Point Stats*\n\n"
        f"Total rounds: `{total}`\n"
        f"Average: `{avg:.2f}x`\n"
        f"Minimum: `{mn:.2f}x`\n"
        f"Maximum: `{mx:.2f}x`\n\n"
        f"🔴 Under 2x: `{under2}` ({under2/total*100:.1f}%)\n"
        f"🟡 2x – 10x: `{between2_10}` ({between2_10/total*100:.1f}%)\n"
        f"🟢 Over 10x: `{over10}` ({over10/total*100:.1f}%)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Clear all stored data."""
    crash_history.clear()
    save_data()
    await update.message.reply_text("🗑️ All crash data cleared.")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎯 *1xbet Crash Tracker*\n\n"
        "/start — begin auto-scraping\n"
        "/stop — stop scraping\n"
        "/history [n] — last N results (default 20)\n"
        "/stats — overall statistics\n"
        "/clear — wipe saved data\n"
        "/help — this message"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("help", cmd_help))

    log.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
