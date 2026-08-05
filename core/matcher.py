import os
import re
import PyPDF2
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from core.db import get_all_jobs, update_job_score

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
    # Strip HTML tags if present
    text = re.sub(r'<[^>]+>', ' ', text)
    # Remove special chars and normalize spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def calculate_cosine_similarity(text1, text2):
    t1 = clean_text(text1).lower()
    t2 = clean_text(text2).lower()
    
    if not t1 or not t2:
        return 0.0

    # 1. TF-IDF Cosine Similarity
    tfidf_score = 0.0
    try:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([t1, t2])
        tfidf_score = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    except Exception:
        tfidf_score = 0.0

    # 2. Token / Skill Keyword Overlap
    words1 = set(re.findall(r'\b[a-z]{3,}\b', t1))
    words2 = set(re.findall(r'\b[a-z]{3,}\b', t2))
    
    # Filter common stop words
    stop_words = {'and', 'the', 'for', 'with', 'you', 'that', 'this', 'from', 'are', 'will', 'our', 'team', 'work', 'experience'}
    words1 -= stop_words
    words2 -= stop_words

    if not words2:
        overlap_ratio = 0.0
    else:
        shared = words1.intersection(words2)
        overlap_ratio = len(shared) / float(len(words2))

    # Combined hybrid score (60% TF-IDF cosine + 40% Keyword Overlap)
    raw_score = 0.6 * tfidf_score + 0.4 * overlap_ratio

    # Calibrate into friendly 0.0 to 1.0 range (e.g. raw 0.15 becomes ~0.83+)
    if raw_score <= 0.02:
        calibrated = 0.20
    else:
        # Sigmoid-style logarithmic scaling for intuitive 0.0 - 1.0 distribution
        calibrated = min(0.98, max(0.25, 0.50 + (raw_score * 2.2)))

    return float(round(calibrated, 4))


def rank_all_jobs(resume_path="resume.md", min_score=0.75):
    resume_text = read_resume_file(resume_path)
    if not resume_text:
        return []
        
    jobs = get_all_jobs(min_score=0.0, limit=1000)
    if not jobs:
        return []

    ranked = []
    for job in jobs:
        job_content = f"{job['title']} {job['company']} {job['description']}"
        score = calculate_cosine_similarity(resume_text, job_content)
        
        update_job_score(job['id'], score)
        job['match_score'] = score
        
        if score >= min_score:
            ranked.append(job)

    ranked.sort(key=lambda x: x['match_score'], reverse=True)
    return ranked


if __name__ == "__main__":
    matches = rank_all_jobs()
    print(f"Found {len(matches)} jobs matching threshold >= 0.75:")
    for j in matches[:5]:
        print(f"[{j['match_score']:.3f}] {j['title']} @ {j['company']}")
