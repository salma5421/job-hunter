import sys
import argparse
import json

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.agent import AntiGravityJobAgent

from core.scraper import run_job_scraper
from core.matcher import rank_all_jobs
from core.cover_letter import generate_cover_letter
from core.interview import generate_interview_questions, evaluate_mock_answer
from core.db import get_all_jobs, get_job_by_id

def main():
    parser = argparse.ArgumentParser(description="Start Working Remotely - AI Job Hunting System")

    parser.add_argument("--scan", action="store_true", help="Scrape new jobs from all sources")
    parser.add_argument("--match", action="store_true", help="Rank jobs against resume")
    parser.add_argument("--query", type=str, default="software engineer", help="Search query/role")
    parser.add_argument("--min-score", type=float, default=0.75, help="Minimum match score (0.0 - 1.0)")
    parser.add_argument("--top", type=int, default=15, help="Number of top matches to display")
    parser.add_argument("--draft", type=str, help="Generate cover letter for specific job_id")
    parser.add_argument("--prep", type=str, help="Generate interview prep questions for job_id")

    args = parser.parse_args()

    if args.scan:
        print(f"🔎 Scanning jobs for '{args.query}'...")
        res = run_job_scraper(search_term=args.query)
        print(f"Scrape Complete: {res['total_scraped']} total jobs found, {res['new_jobs_added']} new jobs cached.")

    elif args.match:
        print(f"🎯 Matching jobs (Threshold >= {args.min_score})...")
        matches = rank_all_jobs(min_score=args.min_score)
        print(f"Found {len(matches)} matches >= {args.min_score}:\n")
        for idx, job in enumerate(matches[:args.top], 1):
            print(f"[{idx}] Score: {job['match_score']:.3f} | {job['title']} @ {job['company']}")
            print(f"    ID: {job['id']} | Source: {job['source']} | URL: {job['url']}\n")

    elif args.draft:
        print(f"✉️ Generating Cover Letter for Job ID: {args.draft}...")
        letter = generate_cover_letter(args.draft)
        print("\n" + "="*50)
        print(letter)
        print("="*50 + "\n")

    elif args.prep:
        print(f"🎤 Generating Interview Prep Questions for Job ID: {args.prep}...")
        q_data = generate_interview_questions(args.prep)
        print("\n" + json.dumps(q_data, indent=2))

    else:
        # Default: run full agent pipeline
        agent = AntiGravityJobAgent(min_score=args.min_score)
        agent.run_pipeline(search_term=args.query)

if __name__ == "__main__":
    main()
