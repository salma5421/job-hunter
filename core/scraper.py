import requests
import sqlite3
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from core.db import save_job, get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scraper")

def generate_unique_id(company, title, url_or_date):
    raw = f"{company.strip().lower()}_{title.strip().lower()}_{str(url_or_date).strip().lower()}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()

import re
import html

def scrape_linkedin(search_term="electronics engineer", location="Egypt"):
    jobs = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={requests.utils.quote(search_term)}&location={requests.utils.quote(location)}&start=0"
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            titles = [html.unescape(re.sub(r'<[^>]+>', '', x).strip()) for x in re.findall(r'<h3[^>]*class="base-search-card__title"[^>]*>(.*?)</h3>', res.text, re.DOTALL)]
            companies = [html.unescape(re.sub(r'<[^>]+>', '', x).strip()) for x in re.findall(r'<h4[^>]*class="base-search-card__subtitle"[^>]*>(.*?)</h4>', res.text, re.DOTALL)]
            locations = [html.unescape(re.sub(r'<[^>]+>', '', x).strip()) for x in re.findall(r'<span[^>]*class="job-search-card__location"[^>]*>(.*?)</span>', res.text, re.DOTALL)]
            urls = re.findall(r'href="(https://[^\s"]+)"', res.text)

            min_len = min(len(titles), len(companies))
            for i in range(min_len):
                t = titles[i]
                c = companies[i]
                l = locations[i] if i < len(locations) else location
                u = urls[i] if i < len(urls) else 'https://www.linkedin.com/jobs'
                unique_id = generate_unique_id(c, t, u)
                jobs.append({
                    'id': unique_id,
                    'title': t,
                    'company': c,
                    'location': l,
                    'description': f"Role position: {t} at {c} in {l}. Full details available on LinkedIn posting.",
                    'url': u,
                    'source': 'LinkedIn',
                    'date_posted': datetime.now().isoformat()
                })
    except Exception as e:
        logger.info(f"LinkedIn fetch skipped/timed out: {e}")
    return jobs

def scrape_remotive(search_term="software engineer"):
    jobs = []
    try:
        url = f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(search_term)}"
        res = requests.get(url, timeout=5)
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
        logger.info(f"Remotive fetch skipped/timed out: {e}")
    return jobs


def scrape_arbeitnow():
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        res = requests.get(url, timeout=5)
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
        logger.info(f"Arbeitnow fetch skipped/timed out: {e}")
    return jobs

def scrape_remoteok():
    jobs = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get("https://remoteok.com/api", headers=headers, timeout=5)
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
        logger.info(f"RemoteOK fetch skipped/timed out: {e}")
    return jobs

def scrape_jobicy():
    jobs = []
    try:
        url = "https://jobicy.com/api/v2/remote-jobs?count=50&geo=any"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
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
        logger.info(f"Jobicy fetch skipped/timed out: {e}")
    return jobs

def scrape_himalayas():
    jobs = []
    try:
        url = "https://himalayas.app/jobs/api?limit=50"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
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
        logger.info(f"Himalayas fetch skipped/timed out: {e}")
    return jobs

def run_job_scraper(search_term="software engineer", location="remote", hours_old=24):
    logger.info(f"Starting lightweight parallel job scrape for: '{search_term}'...")
    all_jobs = []
    
    tasks = [
        lambda: scrape_linkedin("electronics engineer", "Egypt"),
        lambda: scrape_linkedin("software engineer", "Cairo, Egypt"),
        lambda: scrape_linkedin("cybersecurity", "Egypt"),
        lambda: scrape_linkedin("hardware engineer", "Egypt"),
        lambda: scrape_linkedin("technical support", "Egypt"),
        lambda: scrape_linkedin("public relations", "Egypt"),
        lambda: scrape_remotive(search_term),
        lambda: scrape_remotive("electronics"),
        lambda: scrape_remotive("hardware"),
        lambda: scrape_remotive("embedded"),
        lambda: scrape_remotive("cybersecurity"),
        lambda: scrape_remotive("technical support"),
        lambda: scrape_remotive("customer support"),
        lambda: scrape_remotive("python"),
        lambda: scrape_remotive("project manager"),
        scrape_arbeitnow,
        scrape_remoteok,
        scrape_jobicy,
        scrape_himalayas
    ]


    # Execute all API scrapers concurrently in parallel threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(t) for t in tasks]
        for f in as_completed(futures):
            try:
                res = f.result()
                if res:
                    all_jobs.extend(res)
            except Exception as err:
                logger.info(f"Worker task error: {err}")

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
    print("Parallel Scrape Result:", res)

