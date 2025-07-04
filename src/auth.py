# src/auth.py
import streamlit as st
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AuthManager:
    """Manages user authentication and session state."""
    def __init__(self, db_manager):
        self.db = db_manager
        # Initialize session state keys if they don't exist
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None

    def is_authenticated(self) -> bool:
        return st.session_state.get('authenticated', False)

    def get_current_user(self) -> Optional[dict]:
        return st.session_state.get('user')

    def login(self, username, password) -> bool:
        """
        Attempts to log in a user.
        On success, sets session state and returns True.
        On failure, clears session state and returns False.
        """
        user = self.db.authenticate_user(username, password)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user
            return True
        
        # Explicitly clear state on failed login attempt
        st.session_state.authenticated = False
        logger.warning(f"Login failed for user: {username}")
        st.session_state.user = None
        return False

    def logout(self):
        """Logs out the current user by clearing the session state."""
        st.session_state.authenticated = False
        st.session_state.user = None
        # The success message is shown in main.py for better control

    def register(self, username, password) -> bool:
        """Registers a new user."""
        return self.db.create_user(username, password)