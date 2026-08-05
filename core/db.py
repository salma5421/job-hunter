import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jobs_cache.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Jobs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            description TEXT,
            url TEXT,
            source TEXT,
            date_posted TEXT,
            date_scraped TEXT,
            match_score REAL DEFAULT 0.0,
            applied INTEGER DEFAULT 0
        )
    ''')
    
    # Cache / Seen table to prevent duplicate alerts
    c.execute('''
        CREATE TABLE IF NOT EXISTS seen (
            job_id TEXT PRIMARY KEY,
            posted_date TEXT,
            first_seen TEXT
        )
    ''')
    
    # Cover letters table
    c.execute('''
        CREATE TABLE IF NOT EXISTS cover_letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT UNIQUE,
            job_title TEXT,
            company TEXT,
            letter TEXT,
            created_at TEXT,
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        )
    ''')
    
    # Interview prep sessions
    c.execute('''
        CREATE TABLE IF NOT EXISTS interview_prep (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            questions_json TEXT,
            created_at TEXT
        )
    ''')

    conn.commit()
    conn.close()

def save_job(job_dict):
    conn = get_connection()
    c = conn.cursor()
    
    job_id = job_dict.get('id')
    now = datetime.now().isoformat()
    
    c.execute('''
        INSERT OR REPLACE INTO jobs 
        (id, title, company, location, description, url, source, date_posted, date_scraped, match_score, applied)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_id,
        job_dict.get('title', 'Unknown Title'),
        job_dict.get('company', 'Unknown Company'),
        job_dict.get('location', 'Remote'),
        job_dict.get('description', ''),
        job_dict.get('url', ''),
        job_dict.get('source', 'Unknown'),
        job_dict.get('date_posted', now),
        now,
        job_dict.get('match_score', 0.0),
        job_dict.get('applied', 0)
    ))
    
    c.execute('INSERT OR IGNORE INTO seen (job_id, posted_date, first_seen) VALUES (?, ?, ?)',
              (job_id, job_dict.get('date_posted', now), now))
    
    conn.commit()
    conn.close()

def get_all_jobs(min_score=0.0, limit=100):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM jobs WHERE match_score >= ? ORDER BY match_score DESC, date_scraped DESC LIMIT ?', (min_score, limit))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_job_by_id(job_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM jobs WHERE id = ?', (job_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_job_score(job_id, score):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE jobs SET match_score = ? WHERE id = ?', (score, job_id))
    conn.commit()
    conn.close()

def save_cover_letter(job_id, job_title, company, letter):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT OR REPLACE INTO cover_letters (job_id, job_title, company, letter, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (job_id, job_title, company, letter, now))
    conn.commit()
    conn.close()

def get_cover_letter(job_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM cover_letters WHERE job_id = ?', (job_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

# Initialize on module import
init_db()
