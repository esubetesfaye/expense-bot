"""
Google Sheets integration for the Expense Tracker Bot.
- On Railway: reads credentials from GOOGLE_CREDENTIALS_JSON env variable
- On local PC: reads credentials from credentials.json file
Both work automatically with no changes needed!
"""

import os
import json
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
HEADERS = ["Date", "Time", "Description", "Amount (ETB)", "Category", "Logged By"]


class SheetsManager:
    def __init__(self):
        self.spreadsheet_id = os.environ.get("GOOGLE_SHEET_ID")
        self.sheet_name = os.environ.get("SHEET_NAME", "Expenses")
        self.service = self._authenticate()
        self._ensure_headers()

    def _authenticate(self):
        """
        Authenticate using service account credentials.
        - Railway: reads from GOOGLE_CREDENTIALS_JSON environment variable
        - Local PC: reads from credentials.json file
        """
        # Railway mode: credentials stored as environment variable
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            logger.info("Using credentials from environment variable (Railway)")
            creds_info = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        else:
            # Local PC mode: credentials stored as file
            creds_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
            logger.info(f"Using credentials from file (Local PC): {creds_path}")
            creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)

        return build("sheets", "v4", credentials=creds)

    def _ensure_headers(self):
        """Create header row if the sheet is empty."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A1:F1"
            ).execute()

            if not result.get("values"):
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{self.sheet_name}!A1",
                    valueInputOption="RAW",
                    body={"values": [HEADERS]}
                ).execute()
                logger.info("Headers created in sheet.")
        except HttpError as e:
            logger.error(f"Error ensuring headers: {e}")

    def log_expense(self, date: str, time: str, description: str,
                    amount: float, category: str, user: str) -> bool:
        """Append a new expense row to the sheet."""
        try:
            row = [date, time, description, amount, category, user]
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:F",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]}
            ).execute()
            logger.info(f"Logged: {description} - {amount}")
            return True
        except HttpError as e:
            logger.error(f"Error logging expense: {e}")
            return False

    def get_expenses(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetch expenses between start_date and end_date (inclusive).
        Dates should be in YYYY-MM-DD format.
        """
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{self.sheet_name}!A:F"
            ).execute()

            rows = result.get("values", [])
            if not rows or len(rows) < 2:
                return []

            expenses = []
            for row in rows[1:]:
                if len(row) < 4:
                    continue

                row_date = row[0] if len(row) > 0 else ""
                if start_date <= row_date <= end_date:
                    try:
                        expenses.append({
                            "date": row[0],
                            "time": row[1] if len(row) > 1 else "",
                            "description": row[2] if len(row) > 2 else "",
                            "amount": float(row[3]) if len(row) > 3 else 0,
                            "category": row[4] if len(row) > 4 else "📦 Other",
                            "user": row[5] if len(row) > 5 else "",
                        })
                    except (ValueError, IndexError):
                        continue

            return expenses

        except HttpError as e:
            logger.error(f"Error fetching expenses: {e}")
            return []
