import sys
import os
import json
import urllib.parse
import base64
import io
import zipfile
import re
import xml.etree.ElementTree as ET

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from core.db import get_all_jobs, get_job_by_id, get_cover_letter, get_connection
from core.scraper import run_job_scraper
from core.matcher import rank_all_jobs, read_resume_file
from core.cover_letter import generate_cover_letter
from core.interview import generate_interview_questions, evaluate_mock_answer

def app(environ, start_response):
    path = environ.get('PATH_INFO', '/')
    method = environ.get('REQUEST_METHOD', 'GET')
    query_string = environ.get('QUERY_STRING', '')
    query = urllib.parse.parse_qs(query_string)

    headers = [
        ('Content-Type', 'application/json'),
        ('Access-Control-Allow-Origin', '*'),
        ('Access-Control-Allow-Headers', 'Content-Type'),
        ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    ]

    if method == 'OPTIONS':
        start_response('200 OK', headers)
        return [b'']

    # Read body for POST requests
    body = {}
    if method == 'POST':
        try:
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                raw_body = environ['wsgi.input'].read(content_length)
                body = json.loads(raw_body.decode('utf-8'))
        except Exception:
            body = {}

    try:
        # GET Endpoints
        if method == 'GET':
            if path.endswith('/api/status') or path.endswith('/status'):
                conn = get_connection()
                c = conn.cursor()
                c.execute('SELECT COUNT(*) FROM jobs')
                total_jobs = c.fetchone()[0]
                c.execute('SELECT COUNT(*) FROM jobs WHERE match_score >= 0.75')
                top_matches = c.fetchone()[0]
                c.execute('SELECT COUNT(*) FROM cover_letters')
                total_letters = c.fetchone()[0]
                conn.close()

                resume_present = os.path.exists("resume.md") or os.path.exists("resume.txt") or os.path.exists("/tmp/resume.md")
                res_body = json.dumps({
                    "status": "online",
                    "total_jobs": total_jobs,
                    "top_matches": top_matches,
                    "total_letters": total_letters,
                    "resume_present": resume_present
                }).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/jobs') or path.endswith('/jobs'):
                min_score = float(query.get('min_score', [0.0])[0])
                search = query.get('search', [''])[0].lower()
                limit = int(query.get('limit', [100])[0])

                jobs = get_all_jobs(min_score=min_score, limit=limit)
                if search:
                    jobs = [j for j in jobs if search in j['title'].lower() or search in j['company'].lower() or search in j['description'].lower()]

                res_body = json.dumps({"jobs": jobs, "count": len(jobs)}).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/resume') or path.endswith('/resume'):
                text = read_resume_file("resume.md")
                if not text and os.path.exists("/tmp/resume.md"):
                    try:
                        with open("/tmp/resume.md", "r", encoding="utf-8") as f:
                            text = f.read()
                    except Exception:
                        pass
                res_body = json.dumps({"resume": text}).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/config') or path.endswith('/config'):
                cfg = {}
                if os.path.exists("config.json"):
                    with open("config.json", "r") as f:
                        cfg = json.load(f)
                res_body = json.dumps(cfg).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

        # POST Endpoints
        elif method == 'POST':
            if path.endswith('/api/scan') or path.endswith('/scan'):
                search_term = body.get('search_term', 'software engineer')
                location = body.get('location', 'remote')
                res = run_job_scraper(search_term=search_term, location=location)
                rank_all_jobs(min_score=0.0)
                res_body = json.dumps(res).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/match') or path.endswith('/match'):
                min_score = float(body.get('min_score', 0.75))
                matches = rank_all_jobs(min_score=min_score)
                res_body = json.dumps({"matches": matches, "count": len(matches)}).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/resume') or path.endswith('/resume'):
                text = body.get('resume', '')
                for p in ["resume.md", "/tmp/resume.md"]:
                    try:
                        with open(p, "w", encoding="utf-8") as f:
                            f.write(text)
                    except Exception:
                        pass
                rank_all_jobs(min_score=0.0)
                res_body = json.dumps({"success": True, "message": "Resume updated and jobs re-scored!"}).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/upload_cv') or path.endswith('/upload_cv'):
                filename = body.get('filename', 'uploaded_cv.pdf')
                file_b64 = body.get('file_b64', '')
                if not file_b64:
                    start_response('400 Bad Request', headers)
                    return [json.dumps({"error": "No file content provided"}).encode('utf-8')]

                raw_bytes = base64.b64decode(file_b64)
                extracted_text = ""
                if filename.lower().endswith('.pdf'):
                    try:
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
                        for page in pdf_reader.pages:
                            t = page.extract_text()
                            if t:
                                extracted_text += t + "\n"
                    except Exception:
                        pass
                    if not extracted_text.strip():
                        try:
                            raw_str = raw_bytes.decode('latin-1', errors='ignore')
                            found = re.findall(r'\((.*?)\)\s*TJ', raw_str)
                            if not found:
                                found = re.findall(r'\((.*?)\)\s*Tj', raw_str)
                            if found:
                                extracted_text = " ".join(found)
                        except Exception:
                            pass
                elif filename.lower().endswith('.docx'):
                    try:
                        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                            xml_content = z.read('word/document.xml')
                            tree = ET.fromstring(xml_content)
                            texts = [elem.text for elem in tree.iter() if elem.tag.endswith('t') and elem.text]
                            extracted_text = " ".join(texts)
                    except Exception:
                        pass
                else:
                    for enc in ['utf-8', 'latin-1', 'cp1252']:
                        try:
                            extracted_text = raw_bytes.decode(enc)
                            if extracted_text.strip():
                                break
                        except Exception:
                            continue

                if extracted_text.strip():
                    for p in ["resume.md", "/tmp/resume.md"]:
                        try:
                            with open(p, "w", encoding="utf-8") as f:
                                f.write(extracted_text)
                        except Exception:
                            pass
                    matches = rank_all_jobs(min_score=0.0)
                    res_body = json.dumps({
                        "success": True,
                        "filename": filename,
                        "text_preview": extracted_text[:300] + "...",
                        "jobs_rescored": len(matches)
                    }).encode('utf-8')
                    start_response('200 OK', headers)
                    return [res_body]
                else:
                    start_response('400 Bad Request', headers)
                    return [json.dumps({"error": "Could not extract readable text from file."}).encode('utf-8')]

            elif path.endswith('/api/cover_letter') or path.endswith('/cover_letter'):
                job_id = body.get('job_id')
                if not job_id:
                    start_response('400 Bad Request', headers)
                    return [json.dumps({"error": "job_id is required"}).encode('utf-8')]
                letter = generate_cover_letter(job_id)
                res_body = json.dumps({"job_id": job_id, "cover_letter": letter}).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/interview/questions') or path.endswith('/interview/questions'):
                job_id = body.get('job_id')
                questions = generate_interview_questions(job_id)
                res_body = json.dumps(questions).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

            elif path.endswith('/api/interview/evaluate') or path.endswith('/interview/evaluate'):
                question = body.get('question', '')
                answer = body.get('answer', '')
                evaluation = evaluate_mock_answer(question, answer)
                res_body = json.dumps(evaluation).encode('utf-8')
                start_response('200 OK', headers)
                return [res_body]

        start_response('404 Not Found', headers)
        return [json.dumps({"error": f"Endpoint not found: {path}"}).encode('utf-8')]

    except Exception as e:
        start_response('500 Internal Server Error', headers)
        return [json.dumps({"error": str(e)}).encode('utf-8')]

handler = app
