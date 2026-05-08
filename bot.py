"""
Expense Tracker Telegram Bot
Logs expenses to Google Sheets and provides summaries.
"""

import os
import re
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from sheets import SheetsManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SUMMARY_TYPE = 1

# Initialize Google Sheets manager
sheets = SheetsManager()

CATEGORIES = {
    "breakfast": "🍳 Food",
    "lunch": "🍽️ Food",
    "dinner": "🍴 Food",
    "food": "🍽️ Food",
    "coffee": "☕ Food",
    "snack": "🍿 Food",
    "transport": "🚌 Transport",
    "taxi": "🚕 Transport",
    "bus": "🚌 Transport",
    "uber": "🚕 Transport",
    "fuel": "⛽ Transport",
    "groceries": "🛒 Shopping",
    "shopping": "🛍️ Shopping",
    "clothes": "👕 Shopping",
    "health": "💊 Health",
    "medicine": "💊 Health",
    "doctor": "🏥 Health",
    "gym": "💪 Health",
    "rent": "🏠 Housing",
    "electricity": "💡 Bills",
    "internet": "🌐 Bills",
    "phone": "📱 Bills",
    "entertainment": "🎬 Entertainment",
    "movie": "🎬 Entertainment",
    "games": "🎮 Entertainment",
}

def detect_category(description: str) -> str:
    desc_lower = description.lower()
    for keyword, category in CATEGORIES.items():
        if keyword in desc_lower:
            return category
    return "📦 Other"

def parse_expense(text: str):
    """
    Parse expense from message. Supports formats:
    - breakfast 200
    - lunch 150 birr
    - 500 for dinner
    - coffee 50 (treat for team)
    """
    # Pattern: description then amount
    match = re.search(r'^(.+?)\s+(\d+(?:\.\d+)?)\s*(?:birr|etb|br)?(?:\s+.*)?$', text.strip(), re.IGNORECASE)
    if match:
        return match.group(1).strip(), float(match.group(2))

    # Pattern: amount then description
    match = re.search(r'^(\d+(?:\.\d+)?)\s+(?:for\s+)?(.+)$', text.strip(), re.IGNORECASE)
    if match:
        return match.group(2).strip(), float(match.group(1))

    return None, None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to your Expense Tracker Bot!*\n\n"
        "📝 *Log an expense:*\n"
        "Just type the description and amount:\n"
        "`breakfast 200`\n"
        "`taxi 150`\n"
        "`coffee 50 (at office)`\n\n"
        "📊 *Get summaries:*\n"
        "/summary — View expense summary\n"
        "/today — Today's expenses\n"
        "/help — Show this message",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def handle_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Skip commands
    if text.startswith('/'):
        return

    description, amount = parse_expense(text)

    if description is None or amount is None:
        await update.message.reply_text(
            "❓ I couldn't understand that.\n\n"
            "Try: `breakfast 200` or `150 for taxi`",
            parse_mode="Markdown"
        )
        return

    category = detect_category(description)
    now = datetime.now()

    success = sheets.log_expense(
        date=now.strftime("%Y-%m-%d"),
        time=now.strftime("%H:%M"),
        description=description.title(),
        amount=amount,
        category=category,
        user=update.effective_user.first_name or "User"
    )

    if success:
        await update.message.reply_text(
            f"✅ *Logged!*\n\n"
            f"📋 *{description.title()}*\n"
            f"💰 Amount: *{amount:,.0f} ETB*\n"
            f"🏷️ Category: {category}\n"
            f"📅 {now.strftime('%b %d, %Y %H:%M')}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Failed to log expense. Please try again.")


async def summary_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["📅 Daily", "📆 Weekly", "🗓️ Monthly"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "📊 What summary would you like?",
        reply_markup=reply_markup
    )
    return SUMMARY_TYPE


async def summary_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip().lower()

    now = datetime.now()

    if "daily" in choice or "today" in choice:
        period = "today"
        start_date = now.strftime("%Y-%m-%d")
        end_date = start_date
        label = f"Today ({now.strftime('%b %d, %Y')})"
    elif "weekly" in choice or "week" in choice:
        period = "week"
        start_date = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        label = f"This Week ({start_date} → {end_date})"
    elif "monthly" in choice or "month" in choice:
        period = "month"
        start_date = now.replace(day=1).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        label = f"This Month ({now.strftime('%B %Y')})"
    else:
        await update.message.reply_text("Please choose Daily, Weekly, or Monthly.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    expenses = sheets.get_expenses(start_date, end_date)

    if not expenses:
        await update.message.reply_text(
            f"📭 No expenses found for {label}.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Group by category
    categories = {}
    total = 0
    for exp in expenses:
        cat = exp.get("category", "Other")
        amt = exp.get("amount", 0)
        categories[cat] = categories.get(cat, 0) + amt
        total += amt

    # Build message
    lines = [f"📊 *Expense Summary — {label}*\n"]

    # Category breakdown
    lines.append("*By Category:*")
    for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        pct = (amt / total * 100) if total else 0
        bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
        lines.append(f"{cat}: *{amt:,.0f} ETB* ({pct:.0f}%)\n`{bar}`")

    lines.append(f"\n💰 *Total: {total:,.0f} ETB*")
    lines.append(f"🧾 *{len(expenses)} transactions*")

    # Recent transactions
    lines.append("\n*Recent Transactions:*")
    for exp in expenses[-5:]:
        lines.append(f"• {exp['description']} — {exp['amount']:,.0f} ETB ({exp['date']})")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut for today's summary"""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    expenses = sheets.get_expenses(today, today)

    if not expenses:
        await update.message.reply_text(f"📭 No expenses logged today ({now.strftime('%b %d, %Y')}).")
        return

    total = sum(e['amount'] for e in expenses)
    lines = [f"📅 *Today's Expenses — {now.strftime('%b %d, %Y')}*\n"]

    for exp in expenses:
        lines.append(f"• {exp['description']} — *{exp['amount']:,.0f} ETB* {exp.get('category','')}")

    lines.append(f"\n💰 *Total: {total:,.0f} ETB*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    app = Application.builder().token(token).build()

    # Summary conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("summary", summary_start)],
        states={
            SUMMARY_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary_type)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_expense))

    logger.info("Bot started!")
    app.run_polling()


if __name__ == "__main__":
    main()
