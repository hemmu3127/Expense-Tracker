
# src/ui_components.py
import streamlit as st

class UIComponents:
    """Contains methods for rendering reusable UI parts like CSS and login forms."""

    def apply_custom_css(self):
        """Applies custom CSS styling to the Streamlit app."""
        st.markdown("""
            <style>
                /* General Body */
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                }
                /* Main content area */
                .main .block-container {
                    padding-top: 2rem;
                    padding-bottom: 2rem;
                }
                /* Card-like containers */
                .st-emotion-cache-1y4p8pa {
                    border-radius: 10px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    padding: 20px !important;
                }
                /* Buttons */
                .stButton>button {
                    border-radius: 8px;
                    border: 1px solid transparent;
                    transition: all 0.3s;
                }
                .stButton>button:hover {
                    transform: scale(1.02);
                    border: 1px solid #FF4B4B;
                }
                /* Metrics */
                .st-emotion-cache-1k1r3v3 {
                    background-color: #f0f2f6;
                    border-radius: 10px;
                    padding: 15px;
                }
            </style>
        """, unsafe_allow_html=True)

    def render_login_page(self, auth_manager):
        """Renders the login and registration forms."""
        st.title("Welcome to the Smart Expense Tracker 💰")
        st.text("Please login or register to continue.")

        login_tab, register_tab = st.tabs(["Login", "Register"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    if auth_manager.login(username, password):
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with register_tab:
            with st.form("register_form"):
                new_username = st.text_input("Choose a Username")
                new_password = st.text_input("Choose a Password", type="password")
                submitted = st.form_submit_button("Register")
                if submitted:
                    if auth_manager.register(new_username, new_password):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username already exists. Please choose another.")