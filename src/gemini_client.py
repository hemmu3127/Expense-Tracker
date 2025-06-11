# src/gemini_client.py
import json
import logging
import re
from datetime import datetime
from typing import Dict, Optional, List

try:
    from google import generativeai as genai
except ImportError:
    genai = None

logger = logging.getLogger(__name__)

# --- ADDED: Default categories ---
DEFAULT_CATEGORIES: List[str] = [
    "Food & Dining", "Groceries", "Transportation", "Housing", "Utilities",
    "Shopping", "Entertainment", "Health & Wellness", "Education", "Travel",
    "Personal Care", "Gifts & Donations", "Kids", "Pets", "Business", "Miscellaneous"
]

class GeminiClient:
    """Gemini AI client with caching and robust error handling."""
    def __init__(self, api_key: str, db_manager=None):
        # ... (init method is the same) ...
        self.db_manager = db_manager
        self.model = None
        if not genai:
            logger.error("Google Generative AI library not installed.")
            return
        if not api_key:
            logger.error("Gemini API key not provided.")
            return
        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")

    # ... (parse_expense_input method is the same) ...
    def parse_expense_input(self, input_text: str) -> Optional[Dict]:
        if not self.model:
            return None
        prompt = self._build_expense_prompt(input_text)
        if self.db_manager:
            cached_response = self.db_manager.get_cached_response(prompt)
            if cached_response:
                return json.loads(cached_response)
        try:
            response = self.model.generate_content(prompt)
            parsed_data = self._extract_json_from_response(response.text)
            if parsed_data and self._validate_expense_data(parsed_data):
                if self.db_manager:
                    self.db_manager.cache_response(prompt, json.dumps(parsed_data))
                return parsed_data
            return None
        except Exception as e:
            return None

    def _build_expense_prompt(self, input_text: str) -> str:
        """Constructs an optimized prompt for expense parsing."""
        today_date = datetime.now().strftime('%Y-%m-%d')
        # --- ENHANCED: Updated prompt with new categories ---
        category_examples = ", ".join(f"'{cat}'" for cat in DEFAULT_CATEGORIES)
        return f"""
        You are an expert expense parser. Convert the input into a structured JSON object.
        - Fields: category, title, amount, date.
        - Date format must be YYYY-MM-DD. If unspecified, use today: {today_date}.
        - Standardize the category to one of the following: {category_examples}. If it doesn't fit, use 'Miscellaneous'.

        Input: "{input_text}"

        Example Output: {{ "category": "Food & Dining", "title": "Dinner with friends", "amount": 1250, "date": "2024-07-21" }}

        Respond with only the JSON object.
        """

    # ... (other methods are the same) ...
    def _extract_json_from_response(self, text: str) -> Optional[Dict]:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _validate_expense_data(self, data: Dict) -> bool:
        required_fields = ['category', 'title', 'amount', 'date']
        if not all(field in data for field in required_fields): return False
        try:
            float(data['amount'])
            datetime.strptime(data['date'], '%Y-%m-%d')
        except (ValueError, TypeError): return False
        return True