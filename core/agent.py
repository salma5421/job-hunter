import os
import sys
import json
import logging

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.scraper import run_job_scraper
from core.matcher import rank_all_jobs, read_resume_file
from core.cover_letter import generate_cover_letter
from core.interview import generate_interview_questions, evaluate_mock_answer
from core.db import get_all_jobs, get_job_by_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JobHunterAgent")

class StartWorkingRemotelyAgent:
    def __init__(self, resume_path="resume.md", min_score=0.75):
        self.resume_path = resume_path
        self.min_score = min_score

    def run_pipeline(self, search_term="software engineer", location="remote"):
        print("🤖 [Start Working Remotely] Step 1: Scanning job sources (130+ companies & APIs)...")
        scrape_res = run_job_scraper(search_term=search_term, location=location)
        print(f"   📊 Scraped {scrape_res['total_scraped']} total opportunities ({scrape_res['new_jobs_added']} new added to DB)")

        print("\n🎯 [Start Working Remotely] Step 2: Vector Matching & Semantic Scoring against Resume...")

        top_matches = rank_all_jobs(resume_path=self.resume_path, min_score=self.min_score)
        print(f"   ✨ Found {len(top_matches)} top matching jobs with score >= {self.min_score}")

        results = []
        for idx, job in enumerate(top_matches[:5], 1):
            print(f"\n   [{idx}] Score: {job['match_score']:.3f} | {job['title']} @ {job['company']}")
            print(f"       Source: {job['source']} | URL: {job['url']}")
            
            # Step 3: Generate Cover Letter for Top 3 matches
            if idx <= 3:
                print(f"   ✉️ Drafted Cover Letter for {job['title']}...")
                letter = generate_cover_letter(job['id'], resume_path=self.resume_path)
                job['cover_letter'] = letter[:150] + "..."
                
            results.append(job)

        print("\n✅ [Anti-Gravity Agent] Pipeline execution complete!")
        return {
            "scraped_summary": scrape_res,
            "total_matches": len(top_matches),
            "top_matches": results
        }

if __name__ == "__main__":
    agent = AntiGravityJobAgent()
    agent.run_pipeline()
