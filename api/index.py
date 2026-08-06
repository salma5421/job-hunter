import sys
import os
import json
import urllib.parse

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

    try:
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

            resume_present = os.path.exists("resume.md") or os.path.exists("resume.txt")
            body = json.dumps({
                "status": "online",
                "total_jobs": total_jobs,
                "top_matches": top_matches,
                "total_letters": total_letters,
                "resume_present": resume_present
            }).encode('utf-8')
            start_response('200 OK', headers)
            return [body]

        elif path.endswith('/api/jobs') or path.endswith('/jobs'):
            min_score = float(query.get('min_score', [0.0])[0])
            search = query.get('search', [''])[0].lower()
            limit = int(query.get('limit', [100])[0])

            jobs = get_all_jobs(min_score=min_score, limit=limit)
            if search:
                jobs = [j for j in jobs if search in j['title'].lower() or search in j['company'].lower() or search in j['description'].lower()]

            body = json.dumps({"jobs": jobs, "count": len(jobs)}).encode('utf-8')
            start_response('200 OK', headers)
            return [body]

        elif path.endswith('/api/resume') or path.endswith('/resume'):
            if method == 'GET':
                text = read_resume_file("resume.md")
                body = json.dumps({"resume": text}).encode('utf-8')
                start_response('200 OK', headers)
                return [body]

        start_response('404 Not Found', headers)
        return [json.dumps({"error": f"Endpoint not found: {path}"}).encode('utf-8')]
    except Exception as e:
        start_response('500 Internal Server Error', headers)
        return [json.dumps({"error": str(e)}).encode('utf-8')]

handler = app
