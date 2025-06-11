# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from typing import Optional
import calendar

# Import custom modules from src
from src.config import Config
from src.database import DatabaseManager
from src.gemini_client import GeminiClient, DEFAULT_CATEGORIES
from src.voice_processor import VoiceProcessor, MICROPHONE_AVAILABLE
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
        st.rerun()

# --- Main Content Tabs ---
st.title("📈 Expense Dashboard")
tab1, tab2, tab3 = st.tabs(["📊 Overview", "➕ Add Expense", "📤 Export Data"])

# == OVERVIEW TAB ==
with tab1:
    start_date, end_date = None, None
    if view_mode == "Monthly View" and selected_month is not None:
        year_int = int(selected_year)
        _, last_day = calendar.monthrange(year_int, selected_month)
        start_date = datetime(year_int, selected_month, 1).date()
        end_date = datetime(year_int, selected_month, last_day).date()
        month_name = calendar.month_name[selected_month]
        st.subheader(f"Showing Overview for {month_name} {selected_year}")
    elif view_mode == "Yearly View":
        year_int = int(selected_year)
        start_date = datetime(year_int, 1, 1).date()
        end_date = datetime(year_int, 12, 31).date()
        st.subheader(f"Showing Overview for the Year {selected_year}")
    
    st.divider()
    
    dashboard_df = db_manager.get_filtered_expenses(
        user_id=user['id'], start_date=start_date, end_date=end_date,
        categories=selected_categories, amount_range=(0, float('inf'))
    )

    if dashboard_df.empty:
        st.info("No expenses found for the selected period and categories.")
    else:
        total_expense = dashboard_df['amount'].sum()
        avg_expense = dashboard_df['amount'].mean()
        top_category = dashboard_df.groupby('category')['amount'].sum().idxmax()
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"💸 Total Expenses", f"${total_expense:,.2f}")
        c2.metric("📊 Avg. Transaction", f"${avg_expense:,.2f}")
        c3.metric("🏆 Top Category", top_category)
        st.divider()

        c1, c2 = st.columns(2)
        with c1:
            category_dist = dashboard_df.groupby('category')['amount'].sum()
            fig_pie = px.pie(category_dist, values='amount', names=category_dist.index, title="Expense Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            if view_mode == "Monthly View":
                daily_trend = dashboard_df.groupby(dashboard_df['date'].dt.date)['amount'].sum().reset_index()
                fig_trend = px.line(daily_trend, x='date', y='amount', title="Daily Spending Trend", markers=True)
            else:
                dashboard_df['month'] = dashboard_df['date'].dt.strftime('%b')
                monthly_trend = dashboard_df.groupby('month')['amount'].sum().reindex(calendar.month_abbr[1:]).fillna(0).reset_index()
                fig_trend = px.bar(monthly_trend, x='month', y='amount', title="Monthly Spending Trend")
            st.plotly_chart(fig_trend, use_container_width=True)
        
        # --- ENHANCEMENT: Interactive Raw Data list with Delete buttons ---
        with st.expander("View and Manage Transactions"):
            header_cols = st.columns((2, 3, 5, 2, 1))
            header_cols[0].write("**Date**")
            header_cols[1].write("**Category**")
            header_cols[2].write("**Title**")
            header_cols[3].write("**Amount**")
            header_cols[4].write("**Actions**")
            st.markdown("---")

            for index, row in dashboard_df.iterrows():
                col1, col2, col3, col4, col5 = st.columns((2, 3, 5, 2, 1))
                with col1:
                    st.write(row['date'].strftime('%Y-%m-%d'))
                with col2:
                    st.write(row['category'])
                with col3:
                    st.write(row['title'])
                with col4:
                    st.write(f"${row['amount']:,.2f}")
                with col5:
                    if st.button("🗑️", key=f"delete_{row['id']}", help="Delete this transaction"):
                        success = db_manager.delete_expense(expense_id=row['id'], user_id=user['id'])
                        if success:
                            st.toast("Transaction deleted successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to delete transaction.")

# == ADD EXPENSE TAB ==
with tab2:
    st.header("Add a New Expense")
    add_tab1, add_tab2, add_tab3 = st.tabs(["🧠 Smart Add (AI)", "🎤 Voice Add", "✍️ Manual Add"])
    with add_tab1:
        with st.form("smart_add_form", clear_on_submit=True):
            text_input = st.text_input("Describe your expense")
            if st.form_submit_button("✨ Parse and Add") and text_input:
                with st.spinner("🤖 AI is processing..."):
                    expense_data = components['gemini'].parse_expense_input(text_input)
                    if expense_data:
                        expense_data['user_id'] = user['id']
                        db_manager.save_expense(expense_data)
                        st.success("Saved!"); st.rerun()
                    else: st.error("AI could not parse the input.")
    with add_tab2:
        if MICROPHONE_AVAILABLE:
            st.info("Set the thresholds below, then click record.")
            with st.expander("🎙️ Voice Recognition Settings", expanded=True):
                st.markdown("""
                - **Speaking Threshold:** Higher values ignore more background noise.
                - **Pause Threshold:** Higher values let you pause longer while speaking.
                """)
                energy_threshold = st.slider("Speaking Threshold (Energy)", 50, 4000, 300, 50)
                pause_threshold = st.slider("Pause Threshold (seconds)", 0.5, 3.0, 0.8, 0.1)
                st.subheader("Advanced Timing")
                c1, c2 = st.columns(2)
                timeout = c1.number_input("Listening Timeout (s)", 5, 30, 10)
                phrase_limit = c2.number_input("Phrase Time Limit (s)", 5, 60, 15, help="Maximum length of a single voice command.")
            if st.button("🎤 Start Recording", use_container_width=True):
                with st.spinner("Listening... Please start speaking."):
                    voice_result = components['voice'].recognize_speech(
                        energy_threshold=energy_threshold, pause_threshold=pause_threshold,
                        timeout=timeout, phrase_limit=phrase_limit
                    )
                if voice_result['status'] == 'success':
                    st.info(f"Recognized: *{voice_result['text']}*")
                    with st.spinner("🤖 AI is processing..."):
                        expense_data = components['gemini'].parse_expense_input(voice_result['text'])
                        if expense_data:
                            expense_data['user_id'] = user['id']
                            db_manager.save_expense(expense_data)
                            st.success(f"Saved: {expense_data['title']} (${expense_data['amount']})"); st.rerun()
                        else: st.error("AI could not parse the input from your speech.")
                else: st.error(f"Recognition failed: {voice_result['error']}")
        else:
            st.warning("🎤 Voice input is not available on this environment (e.g., Streamlit Cloud). Please use Smart Add or Manual Add.")
            st.info("To enable voice input, run this app on your local machine.")
    with add_tab3:
        with st.form("manual_add_form", clear_on_submit=True):
            user_categories = db_manager.get_user_categories(user['id'])
            combined_categories = sorted(list(set(DEFAULT_CATEGORIES + user_categories)))
            category = st.selectbox("Category", combined_categories + ["+ Add New Category"])
            if category == "+ Add New Category": category = st.text_input("New Category Name")
            title = st.text_input("Title/Description")
            amount = st.number_input("Amount", 0.01, format="%.2f")
            date = st.date_input("Date", datetime.now().date())
            notes = st.text_area("Notes (Optional)")
            if st.form_submit_button("💾 Save Manually") and title and amount and category:
                expense_data = {'user_id': user['id'], 'category': category, 'title': title, 'amount': amount, 'date': date, 'notes': notes}
                db_manager.save_expense(expense_data)
                st.success("Saved!"); st.rerun()

# == EXPORT TAB ==
with tab3:
    st.header("Export Your Data")
    export_period = st.selectbox("Select Export Period", ["Filtered Range", "This Week", "Last Week", "This Month", "Last Month", "This Year"])
    export_start_date, export_end_date = None, None
    if export_period == "Filtered Range":
        st.caption("Select a custom date range for your export.")
        c1, c2 = st.columns(2)
        export_start_date = c1.date_input("From", datetime.now().date() - timedelta(days=30), key="export_start")
        export_end_date = c2.date_input("To", datetime.now().date(), key="export_end")
    else:
        today = datetime.now().date()
        if export_period == "This Week":
            export_start_date, export_end_date = today - timedelta(days=today.weekday()), today
        elif export_period == "Last Week":
            end_of_last_week = today - timedelta(days=today.weekday() + 1)
            export_start_date, export_end_date = end_of_last_week - timedelta(days=6), end_of_last_week
        elif export_period == "This Month":
            export_start_date, export_end_date = today.replace(day=1), today
        elif export_period == "Last Month":
            end_of_last_month = today.replace(day=1) - timedelta(days=1)
            export_start_date, export_end_date = end_of_last_month.replace(day=1), end_of_last_month
        elif export_period == "This Year":
            export_start_date, export_end_date = today.replace(month=1, day=1), today
    all_user_categories = db_manager.get_user_categories(user['id'])
    export_df = db_manager.get_filtered_expenses(user_id=user['id'], start_date=export_start_date, end_date=export_end_date, categories=all_user_categories, amount_range=(0, float('inf')))
    if export_df.empty:
        st.warning(f"No data to export for the selected period: **{export_period}**.")
    else:
        st.info(f"Preparing to export **{len(export_df)}** transactions from **{export_start_date}** to **{export_end_date}**.")
        c1, c2, c3 = st.columns(3)
        file_period_str = export_period.lower().replace(' ', '_')
        c1.download_button("📄 Download as CSV", components['export'].export_to_csv(export_df), f"expenses_{user['username']}_{file_period_str}.csv", "text/csv", use_container_width=True)
        excel_data = components['export'].export_to_excel(export_df)
        c2.download_button("📊 Download as Excel", excel_data.getvalue(), f"expenses_{user['username']}_{file_period_str}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        c3.download_button("📑 Download PDF Report", components['export'].export_to_pdf(export_df, user), f"report_{user['username']}_{file_period_str}.pdf", "application/pdf", use_container_width=True)