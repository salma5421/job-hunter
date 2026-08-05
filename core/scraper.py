import requests
import sqlite3
import hashlib
import json
import logging
from datetime import datetime
from core.db import save_job, get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

def generate_unique_id(company, title, url_or_date):
    raw = f"{company.strip().lower()}_{title.strip().lower()}_{str(url_or_date).strip().lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

def scrape_remotive(search_term="software engineer"):
    jobs = []
    try:
        url = f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(search_term)}"
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('jobs', []):
                unique_id = generate_unique_id(item.get('company_name', ''), item.get('title', ''), item.get('id', ''))
                jobs.append({
                    'id': unique_id,
                    'title': item.get('title', ''),
                    'company': item.get('company_name', ''),
                    'location': item.get('candidate_required_location', 'Remote'),
                    'description': item.get('description', ''),
                    'url': item.get('url', ''),
                    'source': 'Remotive',
                    'date_posted': item.get('publication_date', datetime.now().isoformat())
                })
    except Exception as e:
        logger.error(f"Remotive scraping error: {e}")
    return jobs

def scrape_arbeitnow(search_term="software engineer"):
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('data', []):
                title = item.get('title', '')
                unique_id = generate_unique_id(item.get('company_name', ''), title, item.get('slug', ''))
                jobs.append({
                    'id': unique_id,
                    'title': title,
                    'company': item.get('company_name', ''),
                    'location': item.get('location', 'Remote'),
                    'description': item.get('description', ''),
                    'url': item.get('url', ''),
                    'source': 'Arbeitnow',
                    'date_posted': datetime.now().isoformat()
                })
    except Exception as e:
        logger.error(f"Arbeitnow scraping error: {e}")
    return jobs

def scrape_remoteok(search_term="software engineer"):
    jobs = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get("https://remoteok.com/api", headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                if not isinstance(item, dict) or 'position' not in item:
                    continue
                position = item.get('position', '')
                unique_id = generate_unique_id(item.get('company', ''), position, item.get('id', ''))
                jobs.append({
                    'id': unique_id,
                    'title': position,
                    'company': item.get('company', ''),
                    'location': item.get('location', 'Remote'),
                    'description': item.get('description', ''),
                    'url': item.get('url', 'https://remoteok.com'),
                    'source': 'RemoteOK',
                    'date_posted': item.get('date', datetime.now().isoformat())
                })
    except Exception as e:
        logger.error(f"RemoteOK scraping error: {e}")
    return jobs

def scrape_jobicy(search_term="software engineer"):
    jobs = []
    try:
        url = f"https://jobicy.com/api/v2/remote-jobs?count=50&geo=any"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('jobs', []):
                title = item.get('jobTitle', '')
                unique_id = generate_unique_id(item.get('companyName', ''), title, item.get('id', ''))
                jobs.append({
                    'id': unique_id,
                    'title': title,
                    'company': item.get('companyName', ''),
                    'location': item.get('jobGeo', 'Remote'),
                    'description': item.get('jobDescription', ''),
                    'url': item.get('url', ''),
                    'source': 'Jobicy',
                    'date_posted': item.get('pubDate', datetime.now().isoformat())
                })
    except Exception as e:
        logger.error(f"Jobicy scraping error: {e}")
    return jobs

def scrape_himalayas():
    jobs = []
    try:
        url = "https://himalayas.app/jobs/api?limit=50"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data.get('jobs', []):
                title = item.get('title', '')
                unique_id = generate_unique_id(item.get('companyName', ''), title, item.get('guid', ''))
                jobs.append({
                    'id': unique_id,
                    'title': title,
                    'company': item.get('companyName', ''),
                    'location': 'Remote',
                    'description': item.get('description', ''),
                    'url': item.get('applicationUrl', item.get('himalayasUrl', '')),
                    'source': 'Himalayas',
                    'date_posted': datetime.now().isoformat()
                })
    except Exception as e:
        logger.error(f"Himalayas scraping error: {e}")
    return jobs

def scrape_with_jobspy(search_term="software engineer", location="remote", results_wanted=50):
    jobs = []
    try:
        from jobspy import scrape_jobs
        df = scrape_jobs(
            site_name=["indeed", "linkedin", "glassdoor"],
            search_term=search_term,
            location=location,
            results_wanted=results_wanted,
            hours_old=24
        )
        for _, row in df.iterrows():
            company = str(row.get('company', ''))
            title = str(row.get('title', ''))
            date_posted = str(row.get('date_posted', datetime.now().isoformat()))
            unique_id = generate_unique_id(company, title, date_posted)
            jobs.append({
                'id': unique_id,
                'title': title,
                'company': company,
                'location': str(row.get('location', 'Remote')),
                'description': str(row.get('description', '')),
                'url': str(row.get('job_url', '')),
                'source': str(row.get('site', 'JobSpy')),
                'date_posted': date_posted
            })
    except Exception as e:
        logger.warning(f"JobSpy optional fallback: {e}")
    return jobs

def run_job_scraper(search_term="software engineer", location="remote", hours_old=24):
    logger.info(f"Starting multi-source job scrape for: '{search_term}'...")
    all_jobs = []
    
    # Target search queries to maximize result volume across all tech fields
    queries = list(set([search_term, "software engineer", "developer", "full stack", "backend", "python", "ai engineer", "data engineer"]))
    
    for q in queries:
        all_jobs.extend(scrape_remotive(q))

    all_jobs.extend(scrape_arbeitnow(search_term))
    all_jobs.extend(scrape_remoteok(search_term))
    all_jobs.extend(scrape_jobicy(search_term))
    all_jobs.extend(scrape_himalayas())
    all_jobs.extend(scrape_with_jobspy(search_term, location))
    
    # Save into SQLite database with deduplication
    conn = get_connection()
    c = conn.cursor()
    saved_count = 0
    
    for job in all_jobs:
        c.execute("SELECT 1 FROM seen WHERE job_id = ?", (job['id'],))
        if c.fetchone() is None:
            save_job(job)
            saved_count += 1
            
    conn.close()
    logger.info(f"Scraped {len(all_jobs)} total job postings, {saved_count} new unique jobs added to cache.")
    return {
        'total_scraped': len(all_jobs),
        'new_jobs_added': saved_count
    }

if __name__ == "__main__":
    res = run_job_scraper("software engineer")
    print("Multi-Source Scrape Result:", res)
