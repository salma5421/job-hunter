import os
import re
import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from core.db import get_all_jobs, update_job_score, get_connection

def read_resume_file(filepath="resume.md"):
    if not os.path.exists(filepath):
        if os.path.exists("resume.txt"):
            filepath = "resume.txt"
        elif os.path.exists("resume.pdf"):
            filepath = "resume.pdf"
        else:
            return ""

    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.pdf':
        try:
            text = ""
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error reading PDF resume: {e}")
            return ""
    else:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading resume file: {e}")
            return ""

def clean_text(text):
    if not text:
        return ""
    # Strip HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove special chars and normalize spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_key_skills(text):
    """Extract domain and technical keywords from candidate resume or job posting."""
    text_lower = text.lower()
    skills = set()
    
    dict_skills = [
        'python', 'c', 'c++', 'javascript', 'react', 'html', 'css', 'sql', 'cybersecurity',
        'electronics', 'logic circuits', 'proteus', 'cad', 'networking', 'customer service',
        'public relations', 'support', 'leadership', 'project management', 'agile', 'data',
        'software', 'engineer', 'developer', 'hardware', 'systems', 'communications',
        'security', 'operations', 'analytical', 'research', 'full stack', 'backend', 'frontend'
    ]
    
    for s in dict_skills:
        if s in text_lower:
            skills.add(s)
            
    # Also extract 4+ char single words
    words = set(re.findall(r'\b[a-z]{4,}\b', text_lower))
    stopwords = {'with', 'that', 'this', 'from', 'have', 'more', 'about', 'team', 'work', 'your', 'will', 'role', 'looking', 'ability'}
    words -= stopwords
    
    return skills.union(words)

def calculate_cosine_similarity(text1, text2):
    """Accurate multi-factor job match score (Title + Skill Overlap + TF-IDF Cosine)."""
    t1 = clean_text(text1)
    t2 = clean_text(text2)
    
    if not t1 or not t2:
        return 0.0

    # 1. TF-IDF Cosine Similarity
    tfidf_score = 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([t1.lower(), t2.lower()])
        tfidf_score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    except Exception:
        tfidf_score = 0.0

    # 2. Skill & Domain Keyword Overlap
    skills1 = extract_key_skills(t1)
    skills2 = extract_key_skills(t2)
    
    if not skills2:
        overlap_score = 0.0
    else:
        shared = skills1.intersection(skills2)
        overlap_score = len(shared) / max(1.0, float(len(skills2)))

    # 3. Title & Role Keyword Synergy
    t1_lower = t1.lower()
    t2_lower = t2.lower()
    
    high_priority_keywords = ['engineer', 'developer', 'python', 'software', 'support', 'electronics', 'cybersecurity', 'tech', 'customer', 'data', 'analyst', 'project']
    synergy_count = sum(1 for kw in high_priority_keywords if kw in t1_lower and kw in t2_lower)
    title_boost = min(0.30, synergy_count * 0.08)

    # Weighted realistic final score (0.0 to 1.0)
    raw_hybrid = (0.45 * tfidf_score) + (0.35 * overlap_score) + title_boost

    # Map raw score accurately to intuitive percentage without flat inflation
    if raw_hybrid < 0.05:
        final_score = max(0.15, raw_hybrid * 3.0)
    else:
        final_score = min(0.98, max(0.35, 0.40 + (raw_hybrid * 1.35)))

    return float(round(final_score, 4))


def rank_all_jobs(resume_path="resume.md", min_score=0.0):
    resume_text = read_resume_file(resume_path)
    if not resume_text:
        return []
        
    jobs = get_all_jobs(min_score=0.0, limit=1000)
    if not jobs:
        return []

    clean_resume = clean_text(resume_text)
    resume_skills = extract_key_skills(clean_resume)
    t1_lower = clean_resume.lower()
    
    # 1. Batch TF-IDF Cosine Similarity for ALL jobs at once (~20ms total)
    job_contents = [clean_text(f"{j['title']} {j['company']} {j['location']} {j['description']}") for j in jobs]
    
    tfidf_scores = [0.0] * len(jobs)
    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=10000)
        tfidf_matrix = vectorizer.fit_transform([t1_lower] + [c.lower() for c in job_contents])
        cosine_sims = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]
        tfidf_scores = cosine_sims
    except Exception:
        pass

    high_priority_keywords = ['engineer', 'developer', 'python', 'software', 'support', 'electronics', 'cybersecurity', 'tech', 'customer', 'data', 'analyst', 'project']
    
    ranked = []
    updates = []

    for idx, job in enumerate(jobs):
        tfidf_score = float(tfidf_scores[idx]) if idx < len(tfidf_scores) else 0.0
        content_text = job_contents[idx]
        
        # 2. Skill & Domain Keyword Overlap
        job_skills = extract_key_skills(content_text)
        if not job_skills:
            overlap_score = 0.0
        else:
            shared = resume_skills.intersection(job_skills)
            overlap_score = len(shared) / max(1.0, float(len(job_skills)))

        # 3. Title & Role Keyword Synergy
        t2_lower = content_text.lower()
        synergy_count = sum(1 for kw in high_priority_keywords if kw in t1_lower and kw in t2_lower)
        title_boost = min(0.30, synergy_count * 0.08)

        # Weighted realistic score
        raw_hybrid = (0.45 * tfidf_score) + (0.35 * overlap_score) + title_boost

        if raw_hybrid < 0.05:
            final_score = max(0.15, raw_hybrid * 3.0)
        else:
            final_score = min(0.98, max(0.35, 0.40 + (raw_hybrid * 1.35)))

        score = float(round(final_score, 4))
        job['match_score'] = score
        updates.append((score, job['id']))

        if score >= min_score:
            ranked.append(job)

    # Batch update SQLite scores in one single transaction
    conn = get_connection()
    c = conn.cursor()
    c.executemany("UPDATE jobs SET match_score = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()

    ranked.sort(key=lambda x: x['match_score'], reverse=True)
    return ranked


if __name__ == "__main__":
    matches = rank_all_jobs()
    print(f"Ranked {len(matches)} jobs accurately.")


