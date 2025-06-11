
# src/config.py
import os
from dotenv import load_dotenv
from pathlib import Path

class Config:
    """Manages application configuration by loading environment variables."""
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        self.base_dir = Path(__file__).parent.parent

        # API Keys
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")

        # Database Configuration
        self.database_path = self.base_dir / "data" / "expenses.db"

        if not self.gemini_api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")