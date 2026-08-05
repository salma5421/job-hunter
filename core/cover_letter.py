import os
import requests
import json
import logging
from dotenv import load_dotenv
from core.db import save_cover_letter, get_cover_letter, get_job_by_id
from core.matcher import read_resume_file, clean_text

load_dotenv()
logger = logging.getLogger("cover_letter")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

def generate_with_ollama(prompt, model=OLLAMA_MODEL):
    try:
        url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code == 200:
            return res.json().get('response', '')
    except Exception as e:
        logger.warning(f"Ollama call failed: {e}")
    return None

def generate_with_openrouter(prompt, model="anthropic/claude-3.5-sonnet"):
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        return None
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.warning(f"OpenRouter call failed: {e}")
    return None

def fallback_template_generator(job_title, company, job_desc, resume_text):
    clean_desc = clean_text(job_desc)[:300]
    return f"""Dear Hiring Manager at {company},

I am writing to express my strong enthusiasm for the {job_title} role at {company}. With extensive experience building distributed software systems, high-performing web applications, and AI integrations, I am confident in my ability to bring immediate value to your team.

My technical background aligns directly with your requirements for the {job_title} position. Key highlights from my experience include:
- Designing scalable microservices, REST APIs, and automated data pipelines.
- Implementing semantic search and AI models to streamline engineering workflows.
- Collaborating closely with cross-functional teams to deliver production-ready software on schedule.

I am particularly excited about {company}'s mission and would love the opportunity to contribute to your ongoing projects: "{clean_desc}..."

Thank you for your time and consideration. I welcome the opportunity to discuss how my skill set and passion for engineering fit your needs.

Sincerely,
[Your Name]
candidate@example.com
"""

def generate_cover_letter(job_id, resume_path="resume.md"):
    # Check cache first
    existing = get_cover_letter(job_id)
    if existing:
        return existing['letter']

    job = get_job_by_id(job_id)
    if not job:
        return "Error: Job not found."

    resume_text = read_resume_file(resume_path)
    job_title = job['title']
    company = job['company']
    job_description = job['description']

    prompt = f"""
You are a professional career coach and expert technical copywriter.
Write a concise, compelling, tailored cover letter for the following position:

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION:
{job_description[:1500]}

APPLICANT RESUME:
{resume_text[:2000]}

REQUIREMENTS:
- Maximum 300 words.
- Professional, confident, enthusiastic tone.
- Match key technical skills from resume directly to job requirements.
- ATS-friendly standard formatting. No placeholder tags except standard contact info.
"""

    # 1. Try Ollama (Local)
    letter = generate_with_ollama(prompt)

    # 2. Try OpenRouter (Cloud)
    if not letter:
        letter = generate_with_openrouter(prompt)

    # 3. Fallback engine
    if not letter:
        letter = fallback_template_generator(job_title, company, job_description, resume_text)

    save_cover_letter(job_id, job_title, company, letter)
    return letter

if __name__ == "__main__":
    print("Cover Letter Engine ready.")
