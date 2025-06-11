# 🚀 Smart Expense Tracker

A modern, AI-powered expense tracking application built with Streamlit and Google Gemini. This tool allows users to track expenses via text, voice, or bulk CSV upload, visualize spending patterns, and export reports.

🔒 Secure User Authentication: Multi-user support with a robust login system and hashed passwords to keep your data secure.
🗣️ AI-Powered Expense Parsing: Use natural language to add expenses quickly. Just type something like "Lunch with a client 1200 rupees yesterday" and the AI will handle the rest.
🎙️ Robust Voice Input: Add expenses hands-free. This feature includes configurable settings for noise cancellation and pause detection, making it reliable even in noisy environments.
📊 Interactive Dashboard: Visualize your finances with a powerful dashboard. Switch seamlessly between a detailed Monthly View and a high-level Yearly View to understand your spending patterns.
🔍 Dynamic Dashboard Filtering: Instantly filter your dashboard overview by year, month, and one or more categories to drill down into your spending.
📤 Versatile Data Export: Download your transaction data in multiple formats (CSV, Excel, PDF). Choose from pre-set time periods like "This Week," "Last Month," or a custom date range.
🎨 Modern UI: A clean, stylish, and responsive user interface built with Streamlit, featuring custom styling for a polished user experience.
⚡ Smart Caching: Gemini API calls for AI parsing are cached in the database, which reduces API costs and provides faster responses for repeated queries.


expense-tracker/
├── .env
├── README.md
├── requirements.txt
├── main.py
├── data/
└── src/
├── auth.py
├── config.py
├── database.py
├── export_manager.py
├── gemini_client.py
├── ui_components.py
└── voice_processor.py
## ⚙️ Setup and Installation

1.  **Clone the Repository**
    ```bash
    git clone [<repository-url>](https://github.com/hemmu3127/Expense-Tracker.git)
    cd expense-tracker
    ```

2.  **Create a Virtual Environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**
    -   Create a file named `.env` in the root directory.
    -   Add your Google Gemini API key to it:
        ```ini
        GOOGLE_API_KEY="YOUR_GEMINI_API_KEY_HERE"
        ```

## ▶️ How to Run

Execute the following command from the root directory of the project:

```bash
streamlit run main.py
