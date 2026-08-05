@echo off
echo ========================================================
echo 🌐 Setting up Start Working Remotely...
echo ========================================================


REM Step 1: Create Virtual Environment if not exists
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Step 2: Install core dependencies
echo Installing requirements...
call .\venv\Scripts\activate.bat
pip install -r requirements.txt

REM Step 3: Run initial job scrape and semantic matching
echo Running initial job scrape and resume vector indexing...
python main_agent.py --scan --query "software engineer"
python main_agent.py --match --min-score 0.75

echo ========================================================
echo ✅ Setup complete! Starting Web Application Server...
echo Open your browser at http://localhost:5000
echo ========================================================
python server.py
