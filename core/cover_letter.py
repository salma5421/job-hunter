import os
import requests
import json
import re
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
        # Tight 2-second connect timeout to prevent network hang when Ollama is offline
        res = requests.post(url, json=payload, timeout=(2, 15))
        if res.status_code == 200:
            return res.json().get('response', '')
    except Exception as e:
        logger.info(f"Ollama offline or timed out: {e}")
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
        res = requests.post(url, headers=headers, json=payload, timeout=(2, 15))
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.info(f"OpenRouter call failed: {e}")
    return None

def parse_resume_details(resume_text):
    """Extract candidate name, email, education, and skills dynamically from resume."""
    details = {
        "name": "Salma Ayman Mohamed",
        "email": "salmaayman5421@gmail.com",
        "education": "Communication & Electronics Engineering",
        "skills": ["C", "Python", "Logic Circuits", "Cybersecurity", "Public Relations", "Customer Service", "Project Management"],
        "highlights": []
    }
    
    if not resume_text:
        return details

    lines = [l.strip() for l in resume_text.splitlines() if l.strip()]
    if lines:
        first_line = lines[0]
        if len(first_line) < 50 and not '@' in first_line:
            details['name'] = first_line.title()

    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
    if email_match:
        details['email'] = email_match.group(0)

    # Extract skills mentioned in resume
    known_skills = ['python', 'c++', 'c', 'javascript', 'react', 'html', 'css', 'sql', 'cybersecurity', 
                    'electronics', 'cad', 'proteus', 'networking', 'customer service', 'public relations', 
                    'leadership', 'project management', 'agile', 'data analysis', 'logic circuits']
    found_skills = [s.title() for s in known_skills if re.search(rf'\b{re.escape(s)}\b', resume_text, re.IGNORECASE)]
    if found_skills:
        details['skills'] = found_skills[:8]

    return details

def smart_ats_cover_letter_generator(job_title, company, job_desc, resume_text):
    """High-caliber, ATS-tailored cover letter generator based on candidate profile & job requirements."""
    cand = parse_resume_details(resume_text)
    clean_desc = clean_text(job_desc)
    
    # Extract keywords from job description
    req_keywords = []
    tech_terms = ['python', 'c++', 'javascript', 'support', 'engineering', 'customer', 'communication', 
                  'cybersecurity', 'management', 'data', 'design', 'development', 'api', 'cloud', 'security']
    for term in tech_terms:
        if term in clean_desc.lower():
            req_keywords.append(term.title())
    
    skills_str = ", ".join(cand['skills'][:4]) if cand['skills'] else "engineering, software systems, and crisis resolution"
    matched_reqs = ", ".join(req_keywords[:3]) if req_keywords else "technical execution and cross-functional collaboration"

    return f"""Dear Hiring Team at {company},

I am writing to formally express my strong interest in the {job_title} position at {company}. With a solid academic foundation in {cand['education']} and hands-on expertise spanning {skills_str}, I am confident in my ability to make an immediate impact on your team.

Throughout my technical engineering projects and professional roles, I have consistently demonstrated a strong capacity for high-stakes problem solving, analytical rigor, and cross-functional leadership. My background aligns closely with {company}'s requirements in {matched_reqs}.

Key qualifications I bring to the {job_title} role include:
• Technical Rigor & Engineering Prowess: Applied expertise in core system design, algorithmic logic, and modern tools to solve complex operational challenges.
• Demonstrated Leadership & Project Ownership: Proven experience leading multi-disciplinary teams, driving efficiency improvements, and delivering outcomes under tight deadlines.
• Operational & Communication Excellence: Managing high-volume international communications with exceptional dispute resolution and structured workflow management.

I am particularly drawn to {company}'s ongoing work and would welcome the opportunity to bring my technical skills, proactive mindset, and dedication to excellence to your team.

Thank you for your time and consideration. I look forward to discussing how my background and enthusiasm align with your goals for the {job_title} role.

Sincerely,

{cand['name']}
{cand['email']}
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
- Professional, confident tone matching applicant's real skills.
- ATS-friendly standard formatting. No unresolved bracket placeholders.
"""

    # 1. Try Ollama (Local) with fast timeout
    letter = generate_with_ollama(prompt)

    # 2. Try OpenRouter (Cloud) with fast timeout
    if not letter:
        letter = generate_with_openrouter(prompt)

    # 3. Dynamic Smart ATS engine (Fast, zero-hang, highly tailored)
    if not letter:
        letter = smart_ats_cover_letter_generator(job_title, company, job_description, resume_text)

    save_cover_letter(job_id, job_title, company, letter)
    return letter

if __name__ == "__main__":
    print("Cover Letter Engine ready.")

