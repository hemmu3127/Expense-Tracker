# src/auth.py
import streamlit as st
from typing import Optional

class AuthManager:
    """Manages user authentication and session state."""
    def __init__(self, db_manager):
        self.db = db_manager
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None

    def is_authenticated(self) -> bool:
        return st.session_state.get('authenticated', False)

    def get_current_user(self) -> Optional[dict]:
        return st.session_state.get('user')

    def login(self, username, password) -> bool:
        """Attempts to log in a user by checking the database."""
        user = self.db.authenticate_user(username, password)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user
            return True
        st.session_state.authenticated = False
        st.session_state.user = None
        return False

    def logout(self):
        """Logs out the current user by clearing the session state."""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.success("You have been logged out.")

    def register(self, username, password) -> bool:
        return self.db.create_user(username, password)

    # --- REMOVED: check_remember_me_cookie method ---