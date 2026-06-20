"""
1xbet Crash Point Tracker - Telegram Bot (Manual Mode)
"""

import json
import os
import logging
from datetime import datetime
from collections import deque

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("7487610248:AAEWHVEvI0_lSG3vikD6Dvl4Bxy-kocM2ZU", "7487610248:AAEWHVEvI0_lSG3vikD6Dvl4Bxy-kocM2ZU")
DATA_FILE = "crash_data.json"
MAX_HISTORY = 1000

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ── In-memory store ──────────────────────────────────────────────────────────
crash_history: deque = deque(maxlen=MAX_HISTORY)


# ── Persistence ──────────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                crash_history.extend(data.get("history", []))
                log.info(f"Loaded {len(crash_history)} saved results.")
        except Exception as e:
            log.warning(f"Could not load data: {e}")


def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"history": list(crash_history)}, f, indent=2)
    except Exception as e:
        log.warning(f"Could not save data: {e}")


# ── Handlers ─────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎯 *1xbet Crash Tracker*\n\n"
        "أهلاً! سجل نتائج الـ Crash بسهولة.\n\n"
        "الأوامر:\n"
        "/add 3.45 — أضف نتيجة\n"
        "/history — آخر النتائج\n"
        "/stats — الإحصائيات\n"
        "/clear — امسح البيانات\n"
        "/help — المساعدة"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Add a crash point value. Usage: /add 3.45"""
    if not ctx.args:
        await update.message.reply_text("❌ مثال: `/add 3.45`", parse_mode="Markdown")
        return

    try:
        value = float(ctx.args[0].replace(",", "."))
        if value < 1.0:
            await update.message.reply_text("❌ القيمة يجب أن تكون 1.00 أو أكثر.")
            return

        entry = {
            "value": value,
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }
        crash_history.append(entry)
        save_data()

        await update.message.reply_text(
            f"✅ تم تسجيل: `{value:.2f}x`\n"
            f"📊 إجمالي النتائج: `{len(crash_history)}`",
            parse_mode="Markdown",
        )
    except ValueError:
        await update.message.reply_text("❌ رقم غير صحيح. مثال: `/add 3.45`", parse_mode="Markdown")


async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show last N results."""
    n = 20
    if ctx.args:
        try:
            n = max(1, min(int(ctx.args[0]), 100))
        except ValueError:
            pass

    if not crash_history:
        await update.message.reply_text("📭 لا توجد بيانات بعد. استخدم /add لإضافة نتيجة.")
        return

    items = list(crash_history)[-n:]
    lines = [f"`{e['value']:.2f}x` — {e['time']}" for e in reversed(items)]
    text = f"📋 *آخر {len(items)} نتيجة:*\n\n" + "\n".join(lines)
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show statistics."""
    if not crash_history:
        await update.message.reply_text("📭 لا توجد بيانات بعد.")
        return

    values = [e["value"] for e in crash_history]
    total = len(values)
    avg = sum(values) / total
    mn = min(values)
    mx = max(values)

    under2 = sum(1 for v in values if v < 2)
    between2_10 = sum(1 for v in values if 2 <= v < 10)
    over10 = sum(1 for v in values if v >= 10)

    text = (
        f"📊 *إحصائيات الـ Crash*\n\n"
        f"عدد الجولات: `{total}`\n"
        f"المتوسط: `{avg:.2f}x`\n"
        f"الأدنى: `{mn:.2f}x`\n"
        f"الأعلى: `{mx:.2f}x`\n\n"
        f"🔴 أقل من 2x: `{under2}` ({under2/total*100:.1f}%)\n"
        f"🟡 من 2x إلى 10x: `{between2_10}` ({between2_10/total*100:.1f}%)\n"
        f"🟢 أكثر من 10x: `{over10}` ({over10/total*100:.1f}%)"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    crash_history.clear()
    save_data()
    await update.message.reply_text("🗑️ تم مسح جميع البيانات.")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎯 *1xbet Crash Tracker*\n\n"
        "/add 3.45 — أضف نتيجة crash\n"
        "/history — آخر 20 نتيجة\n"
        "/history 50 — آخر 50 نتيجة\n"
        "/stats — إحصائيات كاملة\n"
        "/clear — امسح كل البيانات\n"
        "/help — هذه القائمة"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("help", cmd_help))

    log.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
