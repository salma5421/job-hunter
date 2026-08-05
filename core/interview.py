import os
import re
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
            'description': 'Engineers with Python, C, APIs, Systems, or Customer Operations background.'
        }
        
    resume_text = read_resume_file(resume_path)
    job_title = job.get('title', 'Engineering Professional')
    company = job.get('company', 'Target Company')
    
    prompt = f"""
Based on the following Job Description and Candidate Resume, generate 15 targeted interview questions.
Group them into 3 categories: "technical", "behavioral", "situational".
Each list item must have:
- "question": string
- "what_interviewer_looks_for": string
- "sample_answer": string (a comprehensive, high-quality candidate answer demonstration)

JOB TITLE: {job_title}
COMPANY: {company}
JOB DESCRIPTION: {job.get('description', '')[:1200]}
RESUME: {resume_text[:1500]}

Return ONLY valid JSON with keys "technical", "behavioral", "situational".
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
        except Exception as e:
            logger.info(f"LLM JSON parsing fallback: {e}")

    # High-caliber role-specific pre-structured question bank with sample answers
    return {
        "technical": [
            {
                "question": f"How do you approach debugging complex system issues or hardware/software logic boundaries in {job_title} projects?",
                "what_interviewer_looks_for": "Structured troubleshooting methodology, isolation of variables, logic simulation tools (e.g. Proteus, CAD, GDB), and signal/data flow tracing.",
                "sample_answer": "I start by isolating the problem domain through systematic input-output testing and behavioral simulation. In my stopwatch and porous material projects, I used Proteus and instrumental analysis to verify signal integrity before physical deployment. When anomalous behavior occurs, I break down the circuit/code into modular components, trace execution logs or timing signals, and resolve root causes iteratively."
            },
            {
                "question": "Can you explain how you manage state, concurrency, and error handling in Python or low-level systems programming?",
                "what_interviewer_looks_for": "Understanding memory safety, locks/async patterns, exception handling, data structures, and edge case resilience.",
                "sample_answer": "In Python, I utilize built-in exception handling (try-except-finally blocks) alongside logging for auditability. For state management, I prefer immutable data structures or explicit class encapsulated states. When working with concurrent tasks or hardware logic, I enforce debouncing and synchronization routines to prevent race conditions and unhandled state transitions."
            },
            {
                "question": "What techniques do you use to optimize performance and prevent bottlenecks in data pipelines or web services?",
                "what_interviewer_looks_for": "Indexing, vectorization, lazy evaluation, caching strategies, and reducing redundant I/O operations.",
                "sample_answer": "I focus on minimizing algorithmic complexity and redundant resource calls. In data processing, I use vectorized operations with tools like scikit-learn or NumPy instead of manual loops. For database and web services, I implement indexed queries, pagination, and response caching to keep response latencies under 200ms."
            },
            {
                "question": "How do you ensure data integrity, authorization, and basic cybersecurity hygiene in public-facing applications?",
                "what_interviewer_looks_for": "Input sanitization, HTTPS encryption, token authentication, rate limiting, and least privilege access principles.",
                "sample_answer": "During my cybersecurity training with NTI & NTRA, I learned to prioritize defense-in-depth. In web services, I ensure all user inputs are strictly sanitized to prevent injection attacks, use HTTPS endpoints, implement token-based authentication, and keep environment secrets isolated using strict environment configuration files."
            },
            {
                "question": "Describe your workflow for writing clean, maintainable code and documenting technical systems for cross-functional teams.",
                "what_interviewer_looks_for": "Modular architecture, docstrings, standardized git commits, README documentation, and clear API contracts.",
                "sample_answer": "I follow clean code principles by maintaining single-responsibility functions and meaningful naming conventions. I document architectural decisions and API specs in structured Markdown (README files) and use Git for granular, semantic commits so team members can easily track and build upon the work."
            }
        ],
        "behavioral": [
            {
                "question": "Tell me about a time you had to lead a team or manage high-pressure operations under tight deadlines.",
                "what_interviewer_looks_for": "STAR method (Situation, Task, Action, Result), delegation, emotional intelligence, and measurable impact.",
                "sample_answer": "As CEO of the Scientific Research Society, I led cross-functional teams to execute major events and launch student internship tracks. When timelines were tight, I audited individual workloads, aligned tasks with team members' strengths, and streamlined team operations—boosting overall operational efficiency by 55% within six months."
            },
            {
                "question": "Describe a situation where you resolved a difficult client or stakeholder conflict under high stress.",
                "what_interviewer_looks_for": "Empathy, active listening, rapid problem-solving, composure, and positive customer retention.",
                "sample_answer": "While working as a Customer Service Agent for Informa Markets, I handled high-volume concurrent inquiries from international contractors and visitors during crisis situations. By actively listening, de-escalating tension in both English and Arabic, and offering swift alternative solutions, I successfully resolved complex disputes and earned the 'Best Customer Service Agent' award."
            },
            {
                "question": f"Why are you interested in joining {company} as a {job_title}?",
                "what_interviewer_looks_for": "Research on company mission, genuine passion, alignment between personal career goals and role responsibilities.",
                "sample_answer": f"I am deeply impressed by {company}'s commitment to innovation and technical excellence. As someone with a background in engineering, analytical problem solving, and leadership, I thrive in environments where technical rigor directly drives tangible business value. This role allows me to leverage my core skills while contributing to {company}'s growth."
            },
            {
                "question": "Give an example of a technical project where things didn't go according to plan. How did you adapt?",
                "what_interviewer_looks_for": "Adaptability, resilience, root-cause analysis, and learning from failure.",
                "sample_answer": "During the Digital Stopwatch hardware assembly, initial timing signals suffered from mechanical switch bounce noise. Instead of abandoning the design, I prototyped IC debouncing circuits and validated the timing behavioral model in Proteus simulation until the circuit operated reliably up to 59:59 without false triggers."
            },
            {
                "question": "How do you prioritize competing tasks when managing multiple initiatives simultaneously?",
                "what_interviewer_looks_for": "Time management, Eisenhower matrix / urgency-impact framing, clear communication with stakeholders.",
                "sample_answer": "I categorize tasks by urgency and long-term strategic impact. Urgent critical-path items get immediate focus, while larger initiatives are broken down into daily milestones. I maintain open communication with team leads to set clear expectations and prevent bottlenecks."
            }
        ],
        "situational": [
            {
                "question": f"If hired at {company}, how would you approach your first 30 to 60 days in this position?",
                "what_interviewer_looks_for": "Proactive onboarding strategy: 30 days learning domain & codebase, 60 days delivering quick wins, 90 days driving independent projects.",
                "sample_answer": f"In the first 30 days, my goal is to absorb {company}'s domain workflows, study existing project architectures, and establish strong relationships with team members. By day 60, I aim to take ownership of core tasks and deliver key feature enhancements or operational improvements."
            },
            {
                "question": "How would you handle a scenario where requirement specs change right before a major project delivery?",
                "what_interviewer_looks_for": "Impact analysis, trade-off communication with product managers, agile scope negotiation.",
                "sample_answer": "I first perform a rapid impact assessment to evaluate technical feasibility and delivery risks. I then meet with project leads to present clear options—such as shipping core functionality first and releasing secondary updates in a follow-up sprint—ensuring quality is never compromised."
            },
            {
                "question": "What steps do you take when evaluating whether to adopt a new tool or framework versus building in-house?",
                "what_interviewer_looks_for": "Cost-benefit balance, maintenance burden, security considerations, and core competency focus.",
                "sample_answer": "I evaluate three factors: development speed, long-term maintenance overhead, and security/compliance. If a battle-tested open-source or commercial tool satisfies 90% of our requirements without vendor lock-in, I advocate adopting it so our team can focus on our core proprietary features."
            },
            {
                "question": "Imagine an external API or key system dependency goes down unexpectedly. How do you respond?",
                "what_interviewer_looks_for": "Graceful degradation, fallback strategies, user-facing error states, monitoring alerts.",
                "sample_answer": "I design systems with defensive architecture. When external dependencies fail, system fallbacks (such as local cached data or graceful degraded states) trigger automatically, while automated alert notifications notify our engineering team with full contextual logs."
            },
            {
                "question": "How do you approach continuous learning when entering an unfamiliar technical domain?",
                "what_interviewer_looks_for": "Growth mindset, hands-on project building, documentation reading, and seeking mentorship.",
                "sample_answer": "I immerse myself through practical application: reading primary documentation, analyzing open-source implementations, and building small end-to-end prototypes. This hands-on loop helps me bridge knowledge gaps quickly and build production confidence."
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
            "feedback": "Your answer is too brief. Try to structure your response using the STAR method (Situation, Task, Action, Result) and include specific technical tools or quantitative outcomes."
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

    # Dynamic intelligent evaluation fallback
    words = candidate_answer.split()
    word_count = len(words)
    answer_lower = candidate_answer.lower()
    
    # Check for strong signals
    has_star_action = any(kw in answer_lower for kw in ['i led', 'i built', 'i implemented', 'i designed', 'my role', 'i resolved', 'i developed', 'we achieved'])
    has_metrics = any(re.search(r'\b\d+(%|k|ms|s|x)?\b', w) for w in words)
    has_tech_keywords = any(kw in answer_lower for kw in ['python', 'c', 'logic', 'circuit', 'api', 'system', 'team', 'process', 'customer', 'data', 'security', 'simulation', 'testing'])

    clarity = min(10, max(5, 5 + (word_count // 20)))
    conciseness = 9 if 35 <= word_count <= 180 else (6 if word_count > 250 else 7)
    impact = 8 if (has_metrics or has_star_action) else 5
    relevance = 9 if has_tech_keywords else 6
    
    overall = round((clarity + conciseness + impact + relevance) / 4.0, 2)

    feedback_tips = []
    if not has_star_action:
        feedback_tips.append("Focus more on explicit personal actions ('I designed...', 'I managed...').")
    if not has_metrics:
        feedback_tips.append("Quantify your achievements with numbers (e.g. '% efficiency gain', 'time saved').")
    if word_count < 35:
        feedback_tips.append("Elaborate further on your problem-solving process and final results.")
    
    if not feedback_tips:
        feedback_tips.append("Excellent structured response! You hit all key technical and behavioral indicators clearly.")

    return {
        "clarity": clarity,
        "conciseness": conciseness,
        "impact": impact,
        "relevance": relevance,
        "overall_score": overall,
        "feedback": " ".join(feedback_tips)
    }

if __name__ == "__main__":
    q = generate_interview_questions("job_123")
    print("Interview Questions Sample loaded successfully.")

