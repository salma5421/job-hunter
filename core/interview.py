import os
import json
import logging
from core.db import get_job_by_id
from core.matcher import read_resume_file
from core.cover_letter import generate_with_ollama, generate_with_openrouter

logger = logging.getLogger("interview")

def generate_interview_questions(job_id, resume_path="resume.md"):
    job = get_job_by_id(job_id)
    if not job:
        job = {
            'title': 'Software Engineer',
            'company': 'Tech Corp',
            'description': 'Senior Backend / Full-Stack Engineer with Python, APIs, and AI background.'
        }
        
    resume_text = read_resume_file(resume_path)
    
    prompt = f"""
Based on the following Job Description and Candidate Resume, generate 15 target interview questions.
Group them into 3 categories:
- 5 Technical Questions
- 5 Behavioral Questions (STAR method)
- 5 Situational / System Design Questions

JOB TITLE: {job['title']}
COMPANY: {job['company']}
JOB DESCRIPTION: {job['description'][:1200]}
RESUME: {resume_text[:1500]}

Format as a structured JSON object with keys: "technical", "behavioral", "situational".
Each list item should have "question" and "what_interviewer_looks_for".
Return ONLY valid JSON.
"""

    res = generate_with_ollama(prompt)
    if not res:
        res = generate_with_openrouter(prompt)
        
    if res:
        try:
            # Extract JSON block if surrounded by markdown code blocks
            if "```json" in res:
                res = res.split("```json")[1].split("```")[0]
            elif "```" in res:
                res = res.split("```")[1].split("```")[0]
            return json.loads(res.strip())
        except Exception as e:
            logger.warning(f"Failed to parse LLM JSON questions: {e}")

    # Fallback pre-structured questions
    return {
        "technical": [
            {
                "question": f"How do you design scalable REST APIs and handle concurrency in Python for {job['title']} positions?",
                "what_interviewer_looks_for": "Understanding of async/await, database connection pooling, caching strategies, and load balancing."
            },
            {
                "question": "Can you explain how vector embeddings and semantic search differ from keyword-based indexing?",
                "what_interviewer_looks_for": "Knowledge of high-dimensional distance metrics (cosine similarity), TF-IDF, vector databases, and indexing speed."
            },
            {
                "question": "What techniques do you use to optimize SQL query performance in heavy database applications?",
                "what_interviewer_looks_for": "Proper indexing, query execution plans, avoiding N+1 queries, partitioning, and caching."
            },
            {
                "question": "How do you handle error boundaries, rate-limiting, and retries in external API integrations?",
                "what_interviewer_looks_for": "Exponential backoff, circuit breakers, idempotent requests, and graceful failure handling."
            },
            {
                "question": "Describe your strategy for automated unit and integration testing in CI/CD pipelines.",
                "what_interviewer_looks_for": "Pytest/Jest test coverage, mock services, integration smoke tests, and automated deployment safety."
            }
        ],
        "behavioral": [
            {
                "question": "Tell me about a time you had to deliver a critical feature under a tight deadline.",
                "what_interviewer_looks_for": "STAR methodology, prioritization, trade-off communication, and stress resilience."
            },
            {
                "question": "Describe a scenario where you disagreed with a technical design decision by a peer or manager.",
                "what_interviewer_looks_for": "Constructive conflict resolution, data-driven argumentation, and team alignment."
            },
            {
                "question": "How do you stay updated with rapidly changing technologies like LLMs and cloud tooling?",
                "what_interviewer_looks_for": "Self-learning mindset, side projects, open-source contributions, and practical experimentation."
            },
            {
                "question": "Give an example of how you mentored a junior engineer or onboarded a new team member.",
                "what_interviewer_looks_for": "Leadership, empathy, documentation standards, and code review practices."
            },
            {
                "question": "Describe a production outage or major bug you caused or investigated. How did you resolve it?",
                "what_interviewer_looks_for": "Post-mortem analysis, root cause diagnosis, blameless culture, and preventive fixes."
            }
        ],
        "situational": [
            {
                "question": f"If hired at {job['company']}, how would you approach architecting a new AI microservice from scratch?",
                "what_interviewer_looks_for": "System breakdown, modularity, security, API contracts, monitoring, and infrastructure."
            },
            {
                "question": "How would you handle a situation where an upstream third-party service API goes down during peak traffic?",
                "what_interviewer_looks_for": "Graceful degradation, fallback defaults, user notifications, and monitoring alerts."
            },
            {
                "question": "How do you evaluate whether to build an in-house tool versus buying or using open-source packages?",
                "what_interviewer_looks_for": "Cost-benefit analysis, maintenance burden, security compliance, and core competency focus."
            },
            {
                "question": "What would you do if a legacy codebase lacks tests and documentation, but needs a core architectural overhaul?",
                "what_interviewer_looks_for": "Characterization tests, incremental refactoring (Strangler Fig pattern), risk mitigation."
            },
            {
                "question": "How do you balance technical debt reduction with shipping new user-facing features?",
                "what_interviewer_looks_for": "Business impact awareness, technical debt budgeting, refactoring alongside features."
            }
        ]
    }

def evaluate_mock_answer(question, candidate_answer):
    if not candidate_answer or len(candidate_answer.strip()) < 5:
        return {
            "clarity": 2,
            "conciseness": 3,
            "impact": 2,
            "relevance": 2,
            "overall_score": 2.25,
            "feedback": "Your answer is too short. Please provide a detailed response with specific examples (e.g. using the STAR method)."
        }

    prompt = f"""
You are an expert tech hiring manager evaluating a candidate's mock interview answer.

QUESTION: {question}
CANDIDATE ANSWER: {candidate_answer}

Rate the candidate on a scale of 1-10 for:
1. Clarity
2. Conciseness
3. Impact
4. Relevance

Provide actionable feedback to improve the answer.

Return ONLY a JSON object with keys: "clarity", "conciseness", "impact", "relevance", "overall_score", "feedback".
"""

    res = generate_with_ollama(prompt)
    if not res:
        res = generate_with_openrouter(prompt)
        
    if res:
        try:
            if "```json" in res:
                res = res.split("```json")[1].split("```")[0]
            elif "```" in res:
                res = res.split("```")[1].split("```")[0]
            return json.loads(res.strip())
        except Exception:
            pass

    # Heuristic evaluation fallback if LLM is offline
    word_count = len(candidate_answer.split())
    clarity = min(10, max(4, word_count // 15 + 4))
    conciseness = 8 if 40 <= word_count <= 200 else 5
    impact = 7 if any(kw in candidate_answer.lower() for kw in ['reduced', 'increased', 'built', 'led', '%', 'latency', 'scale']) else 5
    relevance = 8 if len(candidate_answer) > 50 else 4
    overall = round((clarity + conciseness + impact + relevance) / 4.0, 2)

    return {
        "clarity": clarity,
        "conciseness": conciseness,
        "impact": impact,
        "relevance": relevance,
        "overall_score": overall,
        "feedback": f"Solid effort! You provided {word_count} words. To improve further, quantify your impact with specific metrics (e.g., % improvement, scale handled) and use the STAR method (Situation, Task, Action, Result)."
    }

if __name__ == "__main__":
    q = generate_interview_questions("job_123")
    print("Interview Questions Sample:", json.dumps(q, indent=2))
