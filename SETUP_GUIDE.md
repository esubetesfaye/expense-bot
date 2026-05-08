# 💰 Expense Tracker Telegram Bot — Setup Guide

## What This Bot Does
- Send `breakfast 200` → logs it to Google Sheets instantly
- Send `/summary` → choose Daily, Weekly, or Monthly report
- Send `/today` → quick view of today's expenses

---

## Step 1: Create Your Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., "My Expense Tracker")
4. Choose a username (e.g., `myexpense_bot`) — must end in `bot`
5. BotFather gives you a **token** like: `7123456789:AAFxxxxxxxxxxxxxxxx`
6. Copy and save this token

---

## Step 2: Set Up Google Sheets

### 2a. Create a Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com) and create a new sheet
2. Rename the first tab to **Expenses**
3. Copy the Sheet ID from the URL:
   - URL: `https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit`
   - Sheet ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`

### 2b. Create a Google Service Account
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google Sheets API**:
   - Go to APIs & Services → Library
   - Search "Google Sheets API" → Enable
4. Create Service Account:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → Service Account
   - Name it anything (e.g., "expense-bot")
   - Click Done
5. Download JSON key:
   - Click your service account → Keys tab
   - Add Key → Create new key → JSON
   - Download the file → rename it to `credentials.json`
   - Place it in the same folder as `bot.py`

### 2c. Share Sheet with Service Account
1. Open your `credentials.json` and copy the `client_email` value
   - It looks like: `expense-bot@your-project.iam.gserviceaccount.com`
2. Open your Google Sheet → Click Share
3. Paste that email → set to **Editor** → Share

---

## Step 3: Configure the Bot

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```
   TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxx
   GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
   GOOGLE_CREDENTIALS_PATH=credentials.json
   SHEET_NAME=Expenses
   ```

---

## Step 4: Install & Run

```bash
# Install Python dependencies
pip install -r requirements.txt

# Load environment variables and run
export $(cat .env | xargs) && python bot.py
```

Or on Windows (PowerShell):
```powershell
$env:TELEGRAM_BOT_TOKEN="your_token"
$env:GOOGLE_SHEET_ID="your_sheet_id"
$env:GOOGLE_CREDENTIALS_PATH="credentials.json"
python bot.py
```

---

## Step 5: Test It!

Open your bot in Telegram and try:

| You send | Bot does |
|----------|----------|
| `breakfast 200` | Logs: Description=Breakfast, Amount=200 |
| `taxi 150` | Logs: Description=Taxi, Amount=150, Category=🚕 Transport |
| `coffee 50 (office)` | Logs with note |
| `/today` | Shows today's expenses |
| `/summary` | Asks Daily/Weekly/Monthly then shows report |

---

## Google Sheet Layout

The bot auto-creates headers in row 1:

| Date | Time | Description | Amount (ETB) | Category | Logged By |
|------|------|-------------|--------------|----------|-----------|
| 2025-01-15 | 08:30 | Breakfast | 200 | 🍳 Food | John |
| 2025-01-15 | 12:15 | Taxi | 150 | 🚕 Transport | John |

---

## Auto-Detected Categories

| Keywords | Category |
|----------|----------|
| breakfast, lunch, dinner, coffee, food | 🍽️ Food |
| taxi, uber, bus, transport, fuel | 🚌 Transport |
| groceries, shopping, clothes | 🛒 Shopping |
| medicine, doctor, gym, health | 💊 Health |
| rent | 🏠 Housing |
| electricity, internet, phone | 💡 Bills |
| movie, games, entertainment | 🎬 Entertainment |
| anything else | 📦 Other |

---

## Running Permanently (Optional)

To keep the bot running 24/7 on a Linux server:

```bash
# Using screen
screen -S expensebot
export $(cat .env | xargs) && python bot.py
# Press Ctrl+A then D to detach

# Or using systemd (create /etc/systemd/system/expensebot.service)
```

---

## Troubleshooting

- **"TELEGRAM_BOT_TOKEN not set"** → Make sure your `.env` is loaded before running
- **"Failed to log expense"** → Check that the service account email has Editor access to the sheet
- **Sheet not found** → Verify `GOOGLE_SHEET_ID` is correct and the tab is named "Expenses"
- **credentials.json error** → Make sure the file is in the same directory as `bot.py`
