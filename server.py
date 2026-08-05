import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


from core.db import get_all_jobs, get_job_by_id, get_cover_letter, get_connection
from core.scraper import run_job_scraper
from core.matcher import rank_all_jobs, read_resume_file
from core.cover_letter import generate_cover_letter
from core.interview import generate_interview_questions, evaluate_mock_answer

load_dotenv()

PORT = int(os.getenv("PORT", 5000))
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")

class SystemAPIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        # Suppress routine GET logging for cleaner terminal output
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

    def read_post_json(self):
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len)
        if not post_body:
            return {}
        return json.loads(post_body.decode('utf-8'))

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/api/status':
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
            
            self.send_json({
                "status": "online",
                "total_jobs": total_jobs,
                "top_matches": top_matches,
                "total_letters": total_letters,
                "resume_present": resume_present,
                "port": PORT
            })

        elif path == '/api/jobs':
            min_score = float(query.get('min_score', [0.0])[0])
            search = query.get('search', [''])[0].lower()
            limit = int(query.get('limit', [100])[0])

            jobs = get_all_jobs(min_score=min_score, limit=limit)
            if search:
                jobs = [j for j in jobs if search in j['title'].lower() or search in j['company'].lower() or search in j['description'].lower()]

            self.send_json({"jobs": jobs, "count": len(jobs)})

        elif path == '/api/resume':
            text = read_resume_file("resume.md")
            self.send_json({"resume": text})

        elif path == '/api/config':
            try:
                with open("config.json", "r") as f:
                    cfg = json.load(f)
                self.send_json(cfg)
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        else:
            # Fallback to serving static HTML/CSS/JS files from web/
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.read_post_json()

        if path == '/api/scan':
            search_term = body.get('search_term', 'software engineer')
            location = body.get('location', 'remote')
            res = run_job_scraper(search_term=search_term, location=location)
            # Re-rank jobs automatically after scan
            rank_all_jobs(min_score=0.0)
            self.send_json(res)

        elif path == '/api/match':
            min_score = float(body.get('min_score', 0.75))
            matches = rank_all_jobs(min_score=min_score)
            self.send_json({"matches": matches, "count": len(matches)})

        elif path == '/api/resume':
            text = body.get('resume', '')
            with open("resume.md", "w", encoding="utf-8") as f:
                f.write(text)
            rank_all_jobs(min_score=0.0)
            self.send_json({"success": True, "message": "Resume updated and jobs re-scored!"})

        elif path == '/api/upload_cv':
            import base64
            import io
            import PyPDF2
            
            filename = body.get('filename', 'uploaded_cv.pdf')
            file_b64 = body.get('file_b64', '')
            
            if not file_b64:
                self.send_json({"error": "No file content provided"}, 400)
                return

            try:
                raw_bytes = base64.b64decode(file_b64)
                extracted_text = ""

                if filename.lower().endswith('.pdf'):
                    pdf_reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
                    for page in pdf_reader.pages:
                        extracted_text += page.extract_text() + "\n"
                    with open("resume.pdf", "wb") as f:
                        f.write(raw_bytes)
                else:
                    extracted_text = raw_bytes.decode('utf-8', errors='ignore')

                if extracted_text.strip():
                    with open("resume.md", "w", encoding="utf-8") as f:
                        f.write(extracted_text)
                    with open("resume.txt", "w", encoding="utf-8") as f:
                        f.write(extracted_text)
                    
                    matches = rank_all_jobs(min_score=0.0)
                    self.send_json({
                        "success": True,
                        "filename": filename,
                        "text_preview": extracted_text[:300] + "...",
                        "jobs_rescored": len(matches)
                    })
                else:
                    self.send_json({"error": "Could not extract text from file."}, 400)
            except Exception as e:
                self.send_json({"error": f"Upload error: {e}"}, 500)


        elif path == '/api/cover_letter':
            job_id = body.get('job_id')
            if not job_id:
                self.send_json({"error": "job_id is required"}, 400)
                return
            letter = generate_cover_letter(job_id)
            self.send_json({"job_id": job_id, "cover_letter": letter})

        elif path == '/api/interview/questions':
            job_id = body.get('job_id')
            questions = generate_interview_questions(job_id)
            self.send_json(questions)

        elif path == '/api/interview/evaluate':
            question = body.get('question', '')
            answer = body.get('answer', '')
            evaluation = evaluate_mock_answer(question, answer)
            self.send_json(evaluation)

        elif path == '/api/config':
            try:
                with open("config.json", "w") as f:
                    json.dump(body, f, indent=2)
                self.send_json({"success": True})
            except Exception as e:
                self.send_json({"error": str(e)}, 500)

        else:
            self.send_json({"error": "Endpoint not found"}, 404)

def start_server():
    server = HTTPServer(('0.0.0.0', PORT), SystemAPIHandler)
    print(f"🚀 Start Working Remotely Web Dashboard running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")


if __name__ == "__main__":
    start_server()
