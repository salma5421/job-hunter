# 🌐 Start Working Remotely - AI Job Hunting System

An end-to-end AI-powered Remote Job Hunting & Career System featuring automated job scraping across 130+ sources, TF-IDF vector matching, private LLM cover letter generation, and interactive AI mock interview practice.

---

## 🚀 Key Features

- **🌐 Multi-Source Job Scraper**: Aggregates opportunities across Remotive, RemoteOK, Arbeitnow, Jobicy, Himalayas, and JobSpy APIs.
- **🎯 TF-IDF Semantic Vector Matcher**: Ranks job postings against your resume using scikit-learn cosine similarity & skill keyword overlap.
- **📄 CV / Resume File Uploader**: Drag & drop PDF, TXT, MD, or DOCX resumes; automatically extracts text and re-scores jobs in real time.
- **✉️ Cover Letter Generator**: 100% private ATS-tailored cover letters using local Ollama LLMs, OpenRouter, or built-in copywriting engines.
- **🎤 AI Mock Interviewer & Grader**: Generates 15 role-specific interview questions (technical, behavioral, situational) with instant 1-10 AI scoring and feedback.
- **💎 Modern Web Dashboard**: Premium glassmorphic responsive browser UI (`http://localhost:5000`).

---

## 📦 Project Structure

```
├── web/
│   ├── index.html        # Single-page dashboard GUI
│   ├── styles.css        # Glassmorphic dark-mode CSS design system
│   └── app.js            # Real-time job feed & API client
├── core/
│   ├── scraper.py        # Multi-source job scraper (Remotive, RemoteOK, Jobicy, Himalayas, etc.)
│   ├── matcher.py        # Vector similarity scoring engine
│   ├── cover_letter.py   # Private cover letter generator
│   ├── interview.py      # AI Mock interview & answer evaluator
│   └── db.py             # SQLite persistence layer
├── main_agent.py         # CLI orchestration entry point
├── server.py             # REST API server (Python HTTPServer)
├── requirements.txt      # Dependencies
├── Procfile              # Cloud hosting deployment config
└── render.yaml           # 1-Click Render.com deployment config
```

---

## ⚡ Quick Start

### 1. Install Dependencies
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Launch Web Dashboard
```bash
python server.py
```
Open **`http://localhost:5000`** in your browser.

---

## ☁️ Deployment

### Render.com (Free 24/7 Hosting)
1. Fork or push this repository to GitHub (`https://github.com/salma5421/job-hunter`).
2. Connect your repository to **Render.com** as a Web Service.
3. Render automatically detects `render.yaml` and deploys your live application!
