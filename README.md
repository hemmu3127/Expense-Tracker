# 🚀 Smart Expense Tracker 2.0

A sophisticated, AI-powered expense tracking application built with **Streamlit**, **Google Gemini**, and **Whisper**. This tool allows users to:
- Track expenses via text, voice, or manual entry
- Manage wallet balances
- Visualize spending patterns
- Export detailed reports

---

## ✨ Key Features

- 🧠 **AI-Powered Expense Parsing:**  
  Use natural language to add expenses. Just type  
  `"Lunch with a client 1200 rupees yesterday using UPI"` — Gemini AI parses and categorizes it.

- 🎙️ **Advanced Voice Recognition:**  
  Add expenses hands-free using state-of-the-art transcription.  
  - Powered locally by **OpenAI Whisper** (private, accurate)  
  - Hybrid mode: Combines **Whisper** + **Google Speech Recognition**  
  - Noise robust: Configurable noise cancellation & pause detection

- 💰 **Wallet & Balance Management:**  
  - Track separate balances for UPI and Cash  
  - Auto-deduct from the corresponding wallet

- 📜 **Auditable Activity Log:**  
  - Secure, database-backed log for all actions (add, update, delete, export)

- 📊 **Interactive Dashboard:**  
  - Monthly and yearly views  
  - Filter by year, month, category

- 📤 **Versatile Data Export:**  
  - Export to CSV, Excel, PDF  
  - Includes wallet balance summary  

- 🔒 **Secure Multi-User Authentication:**  
  - Robust login system, hashed passwords

- ⚡ **Smart Caching:**  
  - Reduces API costs, faster Gemini responses

---

## 🏗️ Project Structure

expense-tracker/
├── .streamlit/
│ └── config.toml # Streamlit config
├── .env # Env variables (API Key)
├── README.md
├── requirements.txt
├── main.py # Main app
├── data/ # SQLite DB
├── logs/
│ └── app.log # App logs
└── src/
├── auth.py
├── config.py
├── database.py
├── export_manager.py
├── gemini_client.py
├── ui_components.py
└── voice_processor.py


## ⚙️ Setup and Installation

1️⃣ Clone the Repository
```bash
git clone https://github.com/hemmu3127/Expense-Tracker.git
cd Expense-Tracker
```

2️⃣ Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3️⃣ Install FFmpeg
Required for Whisper:

macOS: 
```bash
brew install ffmpeg
```

Windows: 
``` bash
choco install ffmpeg or scoop install ffmpeg
```

Linux (Debian/Ubuntu):
```bash
sudo apt update && sudo apt install ffmpeg
```

4️⃣ Install Python Dependencies
```bash
pip install -r requirements.txt
```

5️⃣ Configure Environment Variables
Create .env:
```bash 
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY_HERE"
```

▶️ Run the App
```bash
streamlit run main.py
```

🚑 Troubleshooting
If you see:
``` bash
RuntimeError related to torch and __path__._path
```

Run with file watcher disabled:
``` bash
streamlit run main.py --server.fileWatcherType none
```

📌 License
MIT License. Feel free to contribute!



