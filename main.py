# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import calendar
import logging
import os
import warnings

# --- 1. LOGGING CONFIGURATION ---
# Create a logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging to write to a file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="logs/app.log",
    filemode="a",  # Append to the log file on each run
    force=True,    # Force re-configuration, important for Streamlit's re-runs
)
logger = logging.getLogger(__name__)



# --- 2. SUPPRESS SPECIFIC WARNINGS ---
# This ignores the harmless FP16 warning from Whisper on CPU
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")


# --- Import custom modules from src ---
from src.config import Config
from src.database import DatabaseManager
from src.gemini_client import GeminiClient, DEFAULT_CATEGORIES
from src.voice_processor import VoiceProcessor, MICROPHONE_AVAILABLE, WHISPER_AVAILABLE
from src.auth import AuthManager
from src.export_manager import ExportManager
from src.ui_components import UIComponents


# --- Page Configuration ---
st.set_page_config(page_title="Smart Expense Tracker", layout="wide", page_icon="💰")


# --- Initialization ---
@st.cache_resource
def init_components():
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    return {
        'db': db_manager,
        'gemini': GeminiClient(config.gemini_api_key, db_manager),
        'voice': VoiceProcessor(),
        'auth': AuthManager(db_manager),
        'export': ExportManager(),
        'ui': UIComponents()
    }

components = init_components()
components['ui'].apply_custom_css()

# --- Authentication Wall ---
auth_manager = components['auth']
if not auth_manager.is_authenticated():
    st.title("Welcome to the Smart Expense Tracker 💰")
    login_tab, register_tab = st.tabs(["Login", "Register"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if auth_manager.login(username, password):
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Choose a Username")
            new_password = st.text_input("Choose a Password", type="password")
            if st.form_submit_button("Register"):
                if auth_manager.register(new_username, new_password):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Username already exists.")
    st.stop()

# --- Main Application ---
user = auth_manager.get_current_user()
db_manager = components['db']

# --- Sidebar ---
with st.sidebar:
    st.title(f"👋 Welcome, {user['username'].capitalize()}")
    
    # Wallet Balance Display
    wallet = db_manager.get_wallet_balances(user['id'])
    st.metric("💳 UPI Balance", f"${wallet.get('upi_balance', 0):,.2f}")
    st.metric("💵 Cash Balance", f"${wallet.get('cash_balance', 0):,.2f}")

    st.divider()
    st.header("📊 Dashboard Controls")
    view_mode = st.radio("Select View Mode", ["Monthly View", "Yearly View"], horizontal=True)
    available_years = db_manager.get_user_expense_years(user['id']) or [str(datetime.now().year)]
    selected_year = st.selectbox("Select Year", available_years)
    selected_month = None
    if view_mode == "Monthly View":
        month_names = list(calendar.month_name)[1:]
        current_month_index = datetime.now().month - 1
        selected_month_name = st.selectbox("Select Month", month_names, index=current_month_index)
        selected_month = month_names.index(selected_month_name) + 1
    all_user_categories = db_manager.get_user_categories(user['id'])
    selected_categories = st.multiselect("Filter by Category", all_user_categories, default=all_user_categories)
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        auth_manager.logout()
        st.success("You have been logged out.")
        st.rerun()

# --- Main Content Tabs ---
st.title("📈 Expense Dashboard")
logger.info("Application started successfully.")
logger.info(f"User {user['username']} accessed the dashboard.")
tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "💰 My Wallet", "➕ Add Expense", "📤 Export Data"])

# == OVERVIEW TAB ==
with tab1:
    if "editing_expense_id" in st.session_state and st.session_state.editing_expense_id is not None:
        expense_id = st.session_state.editing_expense_id
        expense_to_edit = db_manager.get_expense_by_id(expense_id, user['id'])
        if expense_to_edit:
            @st.dialog("Edit Transaction")
            def show_edit_form():
                with st.form("edit_form"):
                    st.subheader(f"Editing: {expense_to_edit['title']}")
                    user_categories = db_manager.get_user_categories(user['id'])
                    combined_categories = sorted(list(set(DEFAULT_CATEGORIES + user_categories)))
                    
                    try:
                        current_category_index = combined_categories.index(expense_to_edit['category'])
                    except ValueError:
                        combined_categories.append(expense_to_edit['category'])
                        current_category_index = len(combined_categories) - 1
                    
                    c1, c2 = st.columns(2)
                    edited_category = c1.selectbox("Category", combined_categories, index=current_category_index)
                    edited_payment = c2.selectbox("Payment Method", ["UPI", "Cash"], index=["UPI", "Cash"].index(expense_to_edit.get('payment_method', 'Cash')))
                    
                    edited_title = st.text_input("Title/Description", value=expense_to_edit['title'])
                    edited_amount = st.number_input("Amount", min_value=0.01, value=expense_to_edit['amount'], format="%.2f")
                    edited_date = st.date_input("Date", value=pd.to_datetime(expense_to_edit['date']))
                    edited_notes = st.text_area("Notes (Optional)", value=expense_to_edit.get('notes', ''))

                    if st.form_submit_button("💾 Save Changes", use_container_width=True):
                        updated_data = {
                            "category": edited_category, "title": edited_title,
                            "amount": edited_amount, "date": edited_date,
                            "notes": edited_notes, "payment_method": edited_payment
                        }
                        update_result = db_manager.update_expense(expense_id, user['id'], updated_data)
                        if not update_result:
                            st.toast("Transaction updated successfully!")
                            del st.session_state.editing_expense_id
                            st.rerun()
                        else: st.error(update_result)
            show_edit_form()

    year_int = int(selected_year)
    if view_mode == "Monthly View" and selected_month is not None:
        _, last_day = calendar.monthrange(year_int, selected_month)
        start_date, end_date = date(year_int, selected_month, 1), date(year_int, selected_month, last_day)
        st.subheader(f"Overview for {calendar.month_name[selected_month]} {selected_year}")
    else:
        start_date, end_date = date(year_int, 1, 1), date(year_int, 12, 31)
        st.subheader(f"Overview for the Year {selected_year}")
    st.divider()

    dashboard_df = db_manager.get_filtered_expenses(user['id'], start_date, end_date, selected_categories, (0, float('inf')))

    if dashboard_df.empty:
        st.info("No expenses found for the selected period and categories.")
    else:
        total_expense, avg_expense = dashboard_df['amount'].sum(), dashboard_df['amount'].mean()
        top_category = dashboard_df.groupby('category')['amount'].sum().idxmax()
        c1, c2, c3 = st.columns(3)
        c1.metric("💸 Total Expenses", f"${total_expense:,.2f}"); c2.metric("📊 Avg. Transaction", f"${avg_expense:,.2f}"); c3.metric("🏆 Top Category", top_category)
        st.divider()
        
        st.subheader("Visualizations")
        col1, col2 = st.columns(2)
        category_dist = dashboard_df.groupby('category')['amount'].sum().sort_values(ascending=False)
        with col1:
            fig_pie = px.pie(category_dist, values='amount', names=category_dist.index, title="Expense Distribution by Category")
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
            fig_bar = px.bar(category_dist, x=category_dist.index, y='amount', title="Total Spending per Category", labels={'amount':'Total Amount ($)', 'index':'Category'})
            st.plotly_chart(fig_bar, use_container_width=True)

        if view_mode == "Monthly View":
            trend_df = dashboard_df.groupby(dashboard_df['date'].dt.date)['amount'].sum().reset_index()
            fig_trend = px.line(trend_df, x='date', y='amount', title="Daily Spending Trend", markers=True)
        else:
            dashboard_df['month'] = dashboard_df['date'].dt.strftime('%b')
            trend_df = dashboard_df.groupby('month')['amount'].sum().reindex(calendar.month_abbr[1:]).fillna(0).reset_index()
            fig_trend = px.bar(trend_df, x='month', y='amount', title="Monthly Spending Trend")
        st.plotly_chart(fig_trend, use_container_width=True)

        with st.expander("View and Manage Transactions", expanded=True):
            header_cols = st.columns((2, 3, 5, 2, 2, 1, 1))
            headers = ["Date", "Category", "Title", "Amount", "Method", "Actions", ""]
            for i, col in enumerate(header_cols):
                if headers[i]: col.write(f"**{headers[i]}**")
            st.markdown("---")
            for _, row in dashboard_df.iterrows():
                cols = st.columns((2, 3, 5, 2, 2, 1, 1))
                cols[0].write(row['date'].strftime('%Y-%m-%d')); cols[1].write(row['category']); cols[2].write(row['title'])
                cols[3].write(f"${row['amount']:,.2f}")
                method = row.get('payment_method', 'N/A')
                icon = "💳" if method == 'UPI' else "💵"
                cols[4].write(f"{icon} {method}")
                if cols[5].button("✏️", key=f"edit_{row['id']}", help="Edit"): st.session_state.editing_expense_id = row['id']; st.rerun()
                if cols[6].button("🗑️", key=f"delete_{row['id']}", help="Delete"):
                    if db_manager.delete_expense(row['id'], user['id']): st.toast("Deleted!"); st.rerun()
                    else: st.error("Failed to delete.")

with tab2:
    st.header("💰 My Wallet")
    st.info("Set your current available balances. Transactions will automatically deduct from these amounts.")
    current_wallet = db_manager.get_wallet_balances(user['id'])
    with st.form("wallet_form"):
        st.subheader("Update Balances")
        upi_bal = st.number_input("UPI Balance ($)", min_value=0.0, value=current_wallet.get('upi_balance', 0.0), format="%.2f")
        cash_bal = st.number_input("Cash Balance ($)", min_value=0.0, value=current_wallet.get('cash_balance', 0.0), format="%.2f")
        if st.form_submit_button("Save Wallet Balances", use_container_width=True):
            if db_manager.set_wallet_balances(user['id'], upi_bal, cash_bal): st.success("Wallet updated!"); st.rerun()
            else: st.error("Failed to update wallet.")

with tab3:
    st.header("Add a New Expense")
    add_tab1, add_tab2, add_tab3 = st.tabs(["🧠 Smart Add (AI)", "🎤 Voice Add", "✍️ Manual Add"])
    with add_tab1:
        with st.form("smart_add_form", clear_on_submit=True):
            text_input = st.text_input("Describe your expense (e.g., '25 dollars for lunch with card')")
            if st.form_submit_button("✨ Parse and Add") and text_input:
                with st.spinner("🤖 AI is processing..."):
                    expense_data = components['gemini'].parse_expense_input(text_input)
                    if expense_data:
                        expense_data['user_id'] = user['id']
                        result = db_manager.save_expense(expense_data)
                        if not result: st.success("Saved!"); st.rerun()
                        else: st.error(result)
                    else: st.error("AI could not parse input. Please be more specific.")
    
    with add_tab2:
        if MICROPHONE_AVAILABLE:
            available_methods = [m.replace("Speech Recognition", "").strip() for m in components['voice'].get_available_methods()]
            st.info(f"🎤 Available methods: **{', '.join(available_methods)}**")
            
            if WHISPER_AVAILABLE:
                st.success("✅ Enhanced voice recognition with local Whisper AI is available!")
            else:
                st.warning("⚠️ Whisper AI not available, using Google Speech Recognition only.")
            
            st.markdown("Say something like: *'Dinner for 30 dollars paid with cash'*")
            
            with st.expander("🎙️ Voice Settings"):
                method_options = ["Hybrid (Recommended)"] if WHISPER_AVAILABLE else ["Google Only"]
                if WHISPER_AVAILABLE: method_options.extend(["Whisper Only", "Google Only"])
                
                recognition_method = st.selectbox("Recognition Method", method_options, help="Hybrid uses both methods for best accuracy")
                energy = st.slider("Energy Threshold", 50, 4000, 300, 50, key="voice_e")
                pause = st.slider("Pause Threshold (s)", 0.5, 3.0, 0.8, 0.1, key="voice_p")
                timeout = st.slider("Listening Timeout (s)", 5, 30, 10, 1, key="voice_timeout")
                phrase_limit = st.slider("Max Phrase Length (s)", 10, 30, 15, 1, key="voice_phrase")
            
            method_param = "hybrid"
            if "Whisper" in recognition_method: method_param = "whisper"
            elif "Google" in recognition_method: method_param = "google"
            
            if st.button("🎤 Start Recording", use_container_width=True):
                with st.spinner(f"🎧 Listening using {recognition_method}..."):
                    voice_result = components['voice'].recognize_speech(
                        energy_threshold=energy, pause_threshold=pause, timeout=timeout,
                        phrase_limit=phrase_limit, method=method_param
                    )
                
                if voice_result.get('status') == 'success':
                    st.success(f"✅ Recognized via {voice_result['method']}")
                    st.info(f"📝 **Transcription:** *{voice_result['text']}*")
                    
                    if 'confidence' in voice_result:
                        st.progress(max(0, voice_result['confidence'] + 1.0), text=f"Confidence: {voice_result['confidence']:.2f}")

                    with st.spinner("🤖 AI is processing transcription..."):
                        expense_data = components['gemini'].parse_expense_input(voice_result['text'])
                        if expense_data:
                            expense_data['user_id'] = user['id']
                            result = db_manager.save_expense(expense_data)
                            if not result: st.success(f"💾 Saved: {expense_data['title']}!"); st.rerun()
                            else: st.error(f"Failed to save: {result}")
                        else: st.error("🤖 AI could not parse the transcription. Try being more specific.")
                else:
                    st.error(f"❌ Recognition failed ({voice_result.get('method', 'N/A')}): {voice_result.get('error', 'Unknown error')}")

        else:
            st.warning("🎤 Voice input not available - no microphone detected.")
    
    with add_tab3:
        with st.form("manual_add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            category = c1.selectbox("Category", sorted(list(set(DEFAULT_CATEGORIES+db_manager.get_user_categories(user['id'])))) + ["+ Add New Category"])
            if category == "+ Add New Category": category = c1.text_input("New Category Name")
            payment_method = c2.selectbox("Payment Method", ["UPI", "Cash"])
            title = st.text_input("Title/Description")
            amount = st.number_input("Amount", 0.01, format="%.2f")
            date_input = st.date_input("Date", datetime.now().date())
            notes = st.text_area("Notes (Optional)")
            if st.form_submit_button("💾 Save Manually"):
                if title and amount and category and category != "+ Add New Category":
                    expense_data = {'user_id': user['id'], 'category': category, 'title': title, 'amount': amount, 'date': date_input, 'notes': notes, 'payment_method': payment_method}
                    result = db_manager.save_expense(expense_data)
                    if not result: st.success("Saved!"); st.rerun()
                    else: st.error(result)
                else: st.warning("Please fill in all required fields.")

with tab4:
    st.header("Export Your Data")
    # ... (The rest of the file remains the same) ...
    export_period = st.selectbox("Select Export Period", ["Filtered Range", "This Week", "Last Week", "This Month", "Last Month", "This Year"])
    today = datetime.now().date()
    if export_period == "Filtered Range":
        c1, c2 = st.columns(2)
        export_start_date = c1.date_input("From", today - timedelta(days=30), key="export_start")
        export_end_date = c2.date_input("To", today, key="export_end")
    elif export_period == "This Week":
        export_start_date, export_end_date = today - timedelta(days=today.weekday()), today
    elif export_period == "Last Week":
        end_of_last_week = today - timedelta(days=today.weekday() + 1)
        export_start_date, export_end_date = end_of_last_week - timedelta(days=6), end_of_last_week
    elif export_period == "This Month":
        export_start_date, export_end_date = today.replace(day=1), today
    elif export_period == "Last Month":
        end_of_last_month = today.replace(day=1) - timedelta(days=1)
        export_start_date, export_end_date = end_of_last_month.replace(day=1), end_of_last_month
    else: # This Year
        export_start_date, export_end_date = today.replace(month=1, day=1), today

    export_df = db_manager.get_filtered_expenses(user['id'], export_start_date, export_end_date, all_user_categories, (0, float('inf')))
    if export_df.empty:
        st.warning(f"No data to export for the period: **{export_period}**.")
    else:
        st.info(f"Preparing to export **{len(export_df)}** transactions from **{export_start_date}** to **{export_end_date}**.")
        c1, c2, c3 = st.columns(3)
        file_period_str = export_period.lower().replace(' ', '_')
        csv_click=c1.download_button("📄 Download as CSV", components['export'].export_to_csv(export_df), f"expenses_{user['username']}_{file_period_str}.csv", "text/csv", use_container_width=True)
        if csv_click:
            logger.info(f"CSV export initiated for user {user['username']} for period {file_period_str}.")

        excel_data = components['export'].export_to_excel(export_df)
    
        excel_click = c2.download_button("📊 Download as Excel", excel_data.getvalue(), f"expenses_{user['username']}_{file_period_str}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        if excel_click:
            logger.info(f"Excel export initiated for user {user['username']} for period {file_period_str}.")

        pdf_bytes = components['export'].export_to_pdf(export_df, user, wallet)
        pdf_click=c3.download_button("📑 Download PDF Report", pdf_bytes, f"report_{user['username']}_{file_period_str}.pdf", "application/pdf", use_container_width=True)
        if pdf_click:
            logger.info(f"PDF export initiated for user {user['username']} for period {file_period_str}.")