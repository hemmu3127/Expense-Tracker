🚀 Smart Expense Tracker 2.0
A sophisticated, AI-powered expense tracking application built with Streamlit, Google Gemini, and Whisper. This tool allows users to track expenses via text, voice, or manual entry, manage wallet balances, visualize spending patterns, and export detailed reports.
➡️ View Live Demo
✨ Key Features
🧠 AI-Powered Expense Parsing: Use natural language to add expenses. Just type "Lunch with a client 1200 rupees yesterday using UPI" and Gemini AI intelligently parses and categorizes the transaction.
🎙️ Advanced Voice Recognition: Add expenses hands-free using state-of-the-art transcription.
Local & Private: Powered by OpenAI's Whisper model, transcriptions are processed locally on your machine for maximum privacy and accuracy.
Hybrid Mode: Intelligently combines local Whisper and Google Speech Recognition for the best possible results, with automatic fallback.
Noise Robust: Includes configurable settings for noise cancellation and pause detection, making it reliable in various environments.
💰 Wallet & Balance Management:
Track separate balances for UPI and Cash.
Expenses are automatically deducted from the corresponding wallet balance when a transaction is added.
📜 Auditable Activity Log:
A secure, database-backed log tracks every important user action.
Events logged include creating, updating, and deleting transactions, as well as exporting data, providing a complete audit trail.
📊 Interactive Dashboard: Visualize your finances with a powerful dashboard. Switch seamlessly between a detailed Monthly View and a high-level Yearly View to understand your spending patterns.
🔍 Dynamic Filtering: Instantly filter your dashboard overview by year, month, and one or more categories to drill down into your spending.
📤 Versatile Data Export: Download your transaction data in multiple formats (CSV, Excel, PDF). Choose from pre-set time periods like "This Week," "Last Month," or a custom date range. The PDF report also includes a summary of your wallet balances.
🔒 Secure Multi-User Authentication: Robust login system with hashed passwords to keep each user's data secure and separate.
⚡ Smart Caching: Gemini API calls are cached in the database, reducing API costs and providing faster responses for repeated queries.
🏗️ Project Structure
Generated code
expense-tracker/
├── .streamlit/
│   └── config.toml        # Streamlit configuration to silence errors
├── .env                   # Environment variables (API Key)
├── README.md
├── requirements.txt
├── main.py                # Main Streamlit application
│
├── data/                  # SQLite database is stored here
│
├── logs/
│   └── app.log            # Application logs are stored here
│
└── src/
    ├── auth.py
    ├── config.py
    ├── database.py
    ├── export_manager.py
    ├── gemini_client.py
    ├── ui_components.py
    └── voice_processor.py
content_copy
download
Use code with caution.
⚙️ Setup and Installation
Clone the Repository
Generated bash
git clone https://github.com/hemmu3127/Expense-Tracker.git
cd Expense-Tracker
content_copy
download
Use code with caution.
Bash
Create a Virtual Environment
Generated bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
content_copy
download
Use code with caution.
Bash
Install System Dependency: FFmpeg
Whisper requires the ffmpeg tool for audio processing. Install it on your system:
On macOS (using Homebrew):
Generated bash
brew install ffmpeg
content_copy
download
Use code with caution.
Bash
On Windows (using Chocolatey or Scoop):
Generated bash
choco install ffmpeg
# OR
scoop install ffmpeg
content_copy
download
Use code with caution.
Bash
On Linux (Debian/Ubuntu):
Generated bash
sudo apt update && sudo apt install ffmpeg
content_copy
download
Use code with caution.
Bash
Install Python Dependencies
Create a requirements.txt file with the following content, then install from it.
Generated txt
# requirements.txt
streamlit
pandas
plotly-express
google-generativeai
python-dotenv
SpeechRecognition
openai-whisper
torch
pyaudio
fpdf2
openpyxl
content_copy
download
Use code with caution.
Txt
Now run the installation command:
Generated bash
pip install -r requirements.txt
content_copy
download
Use code with caution.
Bash
Configure Environment Variables
Create a file named .env in the root directory.
Add your Google Gemini API key to it:
Generated ini
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY_HERE"
content_copy
download
Use code with caution.
Ini
▶️ How to Run
Execute the following command from the root directory of the project.
Generated bash
streamlit run main.py
content_copy
download
Use code with caution.
Bash
Troubleshooting
If you see a RuntimeError in your console related to torch and __path__._path, it's a known issue with Streamlit's file watcher. You can run the app with the watcher disabled to silence this error. Note: With this command, the app will no longer auto-reload when you save code changes.
Generated bash
streamlit run main.py --server.fileWatcherType none
content_copy
download
Use code with caution.
Bash
