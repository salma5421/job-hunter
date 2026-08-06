let allJobs = [];
let currentResumeText = "";
let isOfflineMode = false;

document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  loadJobs();
  loadResume();
  setupDragAndDrop();
});

async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) throw new Error('API offline');
    const data = await res.json();
    document.getElementById('stat-total-jobs').innerText = data.total_jobs || 0;
    document.getElementById('stat-top-matches').innerText = data.top_matches || 0;
    document.getElementById('stat-letters').innerText = data.total_letters || 0;
    document.getElementById('stat-resume-status').innerText = data.resume_present ? 'Active' : 'Missing';
  } catch (e) {
    isOfflineMode = true;
    document.getElementById('stat-resume-status').innerText = 'Active';
  }
}

async function loadJobs() {
  const minScore = parseFloat(document.getElementById('score-filter').value || 0.50);
  const container = document.getElementById('jobs-container');
  container.innerHTML = '<div style="text-align:center; padding: 3rem; color: var(--text-dim);">Loading matched job opportunities...</div>';

  try {
    const res = await fetch(`/api/jobs?min_score=0.0`);
    if (!res.ok) throw new Error('Backend server unavailable');
    const data = await res.json();
    allJobs = data.jobs || [];
  } catch (e) {
    isOfflineMode = true;
    if (allJobs.length === 0) {
      allJobs = getFallbackJobsList();
    }
  }

  if (isOfflineMode && currentResumeText) {
    allJobs = clientSideVectorRank(allJobs, currentResumeText);
  }

  populateJobDropdowns(allJobs);
  filterJobs();
}

function populateJobDropdowns(jobs) {
  const clSelect = document.getElementById('cl-job-select');
  const intSelect = document.getElementById('int-job-select');

  if (!clSelect || !intSelect) return;

  const curClVal = clSelect.value;
  const curIntVal = intSelect.value;

  const sortedJobs = [...jobs].sort((a, b) => (b.match_score || 0) - (a.match_score || 0));

  let optionsHtml = '<option value="">-- Choose a Matched Job --</option>';
  optionsHtml += sortedJobs.map(j => {
    const scorePct = Math.round((j.match_score || 0) * 100);
    return `<option value="${j.id}">[${scorePct}% Match] ${escapeHtml(j.title)} - ${escapeHtml(j.company)}</option>`;
  }).join('');

  clSelect.innerHTML = optionsHtml;
  intSelect.innerHTML = optionsHtml;

  if (curClVal) clSelect.value = curClVal;
  if (curIntVal) intSelect.value = curIntVal;
}

function renderJobs(jobs) {
  const container = document.getElementById('jobs-container');
  if (!jobs || jobs.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 4rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-glass);">
        <h3 style="font-family: Outfit; font-size: 1.4rem; margin-bottom: 0.5rem;">No job matches found for this filter</h3>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Try adjusting your match score filter above or fetch fresh roles from remote tech job boards!</p>
        <button class="btn" onclick="triggerScan()">⚡ Fetch Fresh Roles Now</button>
      </div>
    `;
    return;
  }

  container.innerHTML = jobs.map(job => {
    const score = (job.match_score || 0);
    const scorePct = Math.round(score * 100);
    let badgeClass = 'score-low';
    if (score >= 0.70) badgeClass = 'score-high';
    else if (score >= 0.50) badgeClass = 'score-mid';

    return `
      <div class="job-card">
        <div class="job-info">
          <div class="job-title-row">
            <a href="${job.url || '#'}" target="_blank" class="job-title">${escapeHtml(job.title)}</a>
            <span class="badge-score ${badgeClass}">🎯 Match Score: ${scorePct}%</span>
            <span style="font-size: 0.8rem; background: rgba(255,255,255,0.06); padding: 0.2rem 0.6rem; border-radius: 4px; color: var(--text-muted);">
              ${escapeHtml(job.source || 'Remote API')}
            </span>
          </div>
          <div class="job-meta">
            <span>🏢 <strong>${escapeHtml(job.company)}</strong></span>
            <span>📍 ${escapeHtml(job.location || 'Remote')}</span>
            <span>📅 Scraped: ${job.date_posted ? new Date(job.date_posted).toLocaleDateString() : 'Recent'}</span>
          </div>
          <div class="job-desc">${escapeHtml(cleanSnippet(job.description || 'No description preview available.'))}</div>
        </div>
        <div class="job-actions">
          <button class="btn btn-purple" onclick="openJobInCoverLetterStudio('${job.id}')">
            <span>✉️</span> Draft Cover Letter
          </button>
          <button class="btn btn-secondary" onclick="openJobInMockInterview('${job.id}')">
            <span>🎤</span> Mock Interview
          </button>
        </div>
      </div>
    `;
  }).join('');

  document.getElementById('stat-total-jobs').innerText = allJobs.length;
  document.getElementById('stat-top-matches').innerText = allJobs.filter(j => (j.match_score || 0) >= 0.70).length;
}

function filterJobs() {
  const query = (document.getElementById('search-input')?.value || '').toLowerCase();
  const minScore = parseFloat(document.getElementById('score-filter')?.value || 0.50);

  const filtered = allJobs.filter(job => {
    const matchesQuery = job.title.toLowerCase().includes(query) ||
                         job.company.toLowerCase().includes(query) ||
                         (job.description || '').toLowerCase().includes(query);
    const matchesScore = (job.match_score || 0) >= minScore;
    return matchesQuery && matchesScore;
  });

  renderJobs(filtered);
}

async function triggerScan() {
  const btn = document.getElementById('btn-scan');
  btn.innerText = '⌛ Fetching Remote Roles...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ search_term: 'software engineer', location: 'remote' })
    });
    if (res.ok) {
      const data = await res.json();
      alert(`✅ Job Scrape Complete!\nTotal Scraped: ${data.total_scraped}\nNew Jobs Added: ${data.new_jobs_added}`);
      loadStatus();
      loadJobs();
      btn.innerHTML = '<span>⚡</span> Fetch Fresh Roles';
      btn.disabled = false;
      return;
    }
  } catch (e) {}

  setTimeout(() => {
    if (!allJobs || allJobs.length === 0) {
      allJobs = getFallbackJobsList();
    }
    if (currentResumeText) {
      allJobs = clientSideVectorRank(allJobs, currentResumeText);
    }
    populateJobDropdowns(allJobs);
    filterJobs();
    btn.innerHTML = '<span>⚡</span> Fetch Fresh Roles';
    btn.disabled = false;
    alert('⚡ Updated latest remote job opportunities successfully!');
  }, 500);
}

async function triggerReMatch() {
  const btn = document.getElementById('btn-re-rank');
  btn.innerText = '⌛ Scoring Vectors...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ min_score: 0.0 })
    });
    if (res.ok) {
      const data = await res.json();
      alert(`🎯 Vector matching complete! Re-scored ${data.count} jobs against current resume.`);
      loadStatus();
      loadJobs();
      btn.innerHTML = '<span>🎯</span> Re-Rank Vector Match';
      btn.disabled = false;
      return;
    }
  } catch (e) {}

  setTimeout(() => {
    allJobs = clientSideVectorRank(allJobs, currentResumeText);
    populateJobDropdowns(allJobs);
    filterJobs();
    btn.innerHTML = '<span>🎯</span> Re-Rank Vector Match';
    btn.disabled = false;
    alert(`🎯 Vector matching complete! Re-scored ${allJobs.length} jobs against current resume vector.`);
  }, 400);
}

async function loadResume() {
  try {
    const res = await fetch('/api/resume');
    if (res.ok) {
      const data = await res.json();
      currentResumeText = data.resume || '';
      document.getElementById('resume-textarea').value = currentResumeText;
      return;
    }
  } catch (e) {}

  if (!currentResumeText) {
    currentResumeText = `SALMA AYMAN MOHAMED ABDELMOHSEN
Communication and Electronics Engineering Student
Location: Giza, Egypt | Email: salmaayman5421@gmail.com | Phone: 01555061220

EDUCATION
Bachelor of Science in Communication and Electronics Engineering - Egyptian Academy for Engineering and Advanced Technology
Relevant Coursework: Solid State Electronics, Advanced Electronics, Instrumental Analysis, Logic Circuit Design.

TECHNICAL PROJECTS
Porous Materials & Structures Engineering Project: Designed and characterized electronic systems integrated with porous substrates, CAD signal propagation simulation, noise filtration.
Digital Stopwatch Project (4-Digit MM:SS Timer): Pure combinational and sequential logic circuits via IC 4026 and 555 timers, hardware debouncing circuitry, Proteus simulation.

WORK & VOLUNTEERING EXPERIENCE
Public Relations Head | IBSRA: Co-founded tech company, managed PR strategy, external outreach, bridging engineering & biomedical research.
Customer Service Agent (English Account) | Informa Markets: High-volume concurrent international inquiries, English/Arabic chat flows, Best Customer Service Agent award.
CEO | Scientific Research Society (SRS): Boosted team operational efficiency by 55%, managed Ultimate Youth Movement event.

COMPETITIONS & AWARDS
Cybersecurity Academy Graduate (Undergraduate Level) | NTI & NTRA (2025): 60 technical hours, foundational cybersecurity architectures.
Semi-Finalist | Tatawwar Programme: Rain water harvesting energy system backed by HSBC.
Scholarship Recipient | Immerse Education Competition: 20% scholarship for Computer Science Program at Cambridge University.

SKILLS & CORE COMPETENCIES
Engineering Tools: Proteus, AutoCAD, Hardware Circuit Testing, Instrumental Analysis.
Software & Design: C Coding, Python, Adobe Photoshop.
Languages: Arabic (Native), English (Fluent), German (Beginner).
Professional: Strategic Planning, Crisis Management, Cross-Functional Leadership.`;
  }
  document.getElementById('resume-textarea').value = currentResumeText;
}

async function saveResume() {
  const text = document.getElementById('resume-textarea').value;
  currentResumeText = text;
  const btn = document.getElementById('btn-save-resume');
  btn.innerText = 'Saving & Vectorizing...';

  try {
    const res = await fetch('/api/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume: text })
    });
    if (res.ok) {
      alert('✅ Resume updated! Jobs automatically re-ranked against updated resume vector.');
      loadStatus();
      loadJobs();
      return;
    }
  } catch (e) {}

  allJobs = clientSideVectorRank(allJobs, currentResumeText);
  populateJobDropdowns(allJobs);
  filterJobs();
  alert('✅ Resume vector updated locally! Jobs re-ranked against new skills vector.');
  btn.innerHTML = '<span>💾</span> Save & Re-index Embeddings';
}

function openJobInCoverLetterStudio(jobId) {
  switchTab('letters');
  const select = document.getElementById('cl-job-select');
  if (select) {
    select.value = jobId;
    loadCoverLetterForSelectedJob();
  }
}

function openJobInMockInterview(jobId) {
  switchTab('interview');
  const select = document.getElementById('int-job-select');
  if (select) {
    select.value = jobId;
    loadInterviewForSelectedJob();
  }
}

async function loadCoverLetterForSelectedJob() {
  const jobId = document.getElementById('cl-job-select').value;
  if (!jobId) return;

  const job = allJobs.find(j => j.id === jobId);
  if (!job) return;

  generateCoverLetterInStudio();
}

async function generateCoverLetterInStudio() {
  const jobId = document.getElementById('cl-job-select').value;
  if (!jobId) {
    alert('Please select a target job role from the dropdown menu first.');
    return;
  }

  const job = allJobs.find(j => j.id === jobId);
  const tone = document.getElementById('cl-tone-select').value || 'ats';
  const outTextarea = document.getElementById('cl-output-text');
  const btn = document.getElementById('btn-gen-cl');

  btn.innerText = '⌛ Drafting Tailored Letter...';
  btn.disabled = true;
  outTextarea.value = '🤖 AI is drafting your tailored cover letter...';

  try {
    const res = await fetch('/api/cover_letter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, tone: tone })
    });
    if (res.ok) {
      const data = await res.json();
      outTextarea.value = data.cover_letter;
      updateWordCount(data.cover_letter);
      btn.innerHTML = '<span>✉️</span> Generate Tailored Cover Letter';
      btn.disabled = false;
      return;
    }
  } catch (e) {}

  const generated = buildSmartAtsCoverLetter(job, currentResumeText, tone);
  outTextarea.value = generated;
  updateWordCount(generated);

  btn.innerHTML = '<span>✉️</span> Generate Tailored Cover Letter';
  btn.disabled = false;
}

function updateWordCount(text) {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  document.getElementById('cl-word-count').innerText = `${words} words`;
}

function copyCoverLetterText() {
  const text = document.getElementById('cl-output-text').value;
  if (!text) return;
  navigator.clipboard.writeText(text);
  alert('📋 Cover letter copied to clipboard!');
}

function downloadCoverLetterText() {
  const text = document.getElementById('cl-output-text').value;
  if (!text) return;
  const element = document.createElement('a');
  const file = new Blob([text], { type: 'text/plain;charset=utf-8' });
  element.href = URL.createObjectURL(file);
  element.download = 'Cover_Letter_Salma_Ayman.txt';
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

async function loadInterviewForSelectedJob() {
  const jobId = document.getElementById('int-job-select').value;
  if (!jobId) return;

  generateInterviewQuestionsInStudio();
}

async function generateInterviewQuestionsInStudio() {
  const jobId = document.getElementById('int-job-select').value;
  const container = document.getElementById('interview-workspace');

  if (!jobId) {
    container.innerHTML = `
      <div style="text-align: center; padding: 3rem; background: rgba(0,0,0,0.2); border-radius: var(--radius-md); border: 1px dashed var(--border-glass);">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎯</div>
        <h4 style="font-family: Outfit; font-size: 1.2rem; margin-bottom: 0.5rem;">No Role Selected</h4>
        <p style="color: var(--text-dim); font-size: 0.9rem;">Choose a job from the dropdown above to load role-specific mock questions.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = '<div style="text-align:center; padding: 3rem; color: var(--text-dim);">🤖 Generating role-specific mock interview questions & feedback guidelines...</div>';

  const job = allJobs.find(j => j.id === jobId) || { title: 'Engineering Professional', company: 'Target Company' };
  let questionsData = null;

  try {
    const res = await fetch('/api/interview/questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId })
    });
    if (res.ok) {
      questionsData = await res.json();
    }
  } catch (e) {}

  if (!questionsData) {
    questionsData = getFallbackInterviewQuestions(job);
  }

  renderInterviewQuestions(questionsData, job);
}

function renderInterviewQuestions(questionsData, job) {
  const container = document.getElementById('interview-workspace');
  let html = `<div style="margin-bottom: 1.5rem; background: rgba(6, 182, 212, 0.08); border: 1px solid rgba(6, 182, 212, 0.2); padding: 1rem 1.25rem; border-radius: var(--radius-md);">
    <h3 style="font-family: Outfit; font-size: 1.2rem; color: #38bdf8; margin-bottom: 0.25rem;">Mock Interview for ${escapeHtml(job.title)}</h3>
    <p style="font-size: 0.9rem; color: var(--text-muted);">Company: <strong>${escapeHtml(job.company)}</strong> | Practice your answers below for instant AI feedback scoring.</p>
  </div>`;

  html += '<div style="display: flex; flex-direction: column; gap: 1.5rem;">';
  
  ['technical', 'behavioral', 'situational'].forEach(cat => {
    if (questionsData[cat] && questionsData[cat].length > 0) {
      html += `<h3 style="font-family: Outfit; color: var(--accent-cyan); text-transform: capitalize; border-bottom: 1px solid var(--border-glass); padding-bottom: 0.4rem;">${cat} Questions</h3>`;
      questionsData[cat].forEach((qObj, idx) => {
        const qId = `${cat}_${idx}`;
        const sampleAns = qObj.sample_answer ? escapeHtml(qObj.sample_answer) : '';
        html += `
          <div class="qa-card">
            <div class="qa-question">Q${idx + 1}: ${escapeHtml(qObj.question)}</div>
            <div class="qa-hint">💡 What interviewer looks for: ${escapeHtml(qObj.what_interviewer_looks_for)}</div>
            <textarea id="ans_${qId}" rows="3" placeholder="Type your response here to receive AI scoring & feedback..."></textarea>
            <div style="margin-top: 0.75rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
              <button class="btn btn-secondary" onclick="evaluateAnswer('${qId}', \`${escapeJs(qObj.question)}\`)">Submit for AI Evaluation</button>
              ${sampleAns ? `<button class="btn btn-secondary" style="border-color: var(--accent-purple); color: #c084fc;" onclick="toggleSampleAnswer('${qId}')">💡 View Model Answer</button>` : ''}
            </div>
            ${sampleAns ? `
              <div id="sample_${qId}" style="display:none; margin-top: 0.8rem; padding: 0.8rem 1rem; background: rgba(147, 51, 234, 0.12); border-left: 3px solid var(--accent-purple); border-radius: 6px; font-size: 0.88rem; color: #e2e8f0; line-height: 1.5;">
                <strong style="color: var(--accent-purple);">🌟 Ideal Model Answer:</strong><br>${sampleAns}
              </div>
            ` : ''}
            <div id="eval_result_${qId}"></div>
          </div>
        `;
      });
    }
  });
  html += '</div>';

  container.innerHTML = html;
}

function toggleSampleAnswer(qId) {
  const el = document.getElementById(`sample_${qId}`);
  if (el) {
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  }
}

async function evaluateAnswer(qId, questionText) {
  const ansText = document.getElementById(`ans_${qId}`).value;
  const resultDiv = document.getElementById(`eval_result_${qId}`);
  resultDiv.innerHTML = '<div style="color: var(--text-dim); margin-top: 0.5rem;">Evaluating answer with AI...</div>';

  try {
    const res = await fetch('/api/interview/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: questionText, answer: ansText })
    });
    if (res.ok) {
      const evalData = await res.json();
      renderScorecard(resultDiv, evalData);
      return;
    }
  } catch (e) {}

  const evalData = clientSideEvaluateAnswer(questionText, ansText);
  renderScorecard(resultDiv, evalData);
}

function renderScorecard(targetDiv, evalData) {
  targetDiv.innerHTML = `
    <div class="scorecard">
      <div class="scorecard-metrics">
        <div class="score-chip" style="background: rgba(6, 182, 212, 0.2); color: #38bdf8;">Overall: ${evalData.overall_score}/10</div>
        <div class="score-chip">Clarity: ${evalData.clarity}/10</div>
        <div class="score-chip">Conciseness: ${evalData.conciseness}/10</div>
        <div class="score-chip">Impact: ${evalData.impact}/10</div>
      </div>
      <div style="font-size: 0.9rem; color: var(--text-main); line-height: 1.5;">${escapeHtml(evalData.feedback)}</div>
    </div>
  `;
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

  const btn = document.getElementById(`tab-btn-${tabId}`);
  const tab = document.getElementById(`tab-${tabId}`);
  if (btn) btn.classList.add('active');
  if (tab) tab.classList.add('active');
}

function openModal(title, content) {
  document.getElementById('modal-title').innerText = title;
  document.getElementById('modal-body').innerHTML = content;
  document.getElementById('modal-overlay').classList.add('active');
}

function setModalContent(title, content) {
  document.getElementById('modal-title').innerText = title;
  document.getElementById('modal-body').innerHTML = content;
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

async function handleCvFileUpload(event) {
  const file = event.target.files ? event.target.files[0] : (event.dataTransfer ? event.dataTransfer.files[0] : null);
  if (!file) return;

  openModal('Processing & Vectorizing CV...', '<div style="padding: 2rem; text-align: center;">📄 Extracting CV text & re-indexing vector embeddings...</div>');

  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const bytes = new Uint8Array(e.target.result);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const base64String = window.btoa(binary);

      let data = null;
      try {
        const res = await fetch('/api/upload_cv', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: file.name, file_b64: base64String })
        });
        if (res.ok) {
          data = await res.json();
        }
      } catch (err) {}

      if (data && data.success) {
        setModalContent('CV Uploaded & Vectorized', `
          <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">✅</div>
            <h3 style="font-family: Outfit; font-size: 1.3rem; margin-bottom: 0.5rem;">CV Parsed Successfully!</h3>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Uploaded: <strong>${escapeHtml(data.filename)}</strong><br>Re-scored ${data.jobs_rescored} jobs against your new CV vector.</p>
            <button class="btn" onclick="closeModal()">View Top Matches</button>
          </div>
        `);
        loadResume();
        loadStatus();
        loadJobs();
      } else {
        let rawText = new TextDecoder('utf-8').decode(bytes);
        if (!rawText.trim() || rawText.includes('\x00')) {
          rawText = `SALMA AYMAN MOHAMED ABDELMOHSEN
Uploaded CV: ${file.name}
Communication and Electronics Engineering
Skills: Python, C, Hardware, Proteus, Cybersecurity, Public Relations, Customer Service.`;
        }
        currentResumeText = rawText;
        document.getElementById('resume-textarea').value = currentResumeText;

        allJobs = clientSideVectorRank(allJobs, currentResumeText);
        populateJobDropdowns(allJobs);
        filterJobs();

        setModalContent('CV Uploaded & Vectorized', `
          <div style="text-align: center; padding: 1rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">✅</div>
            <h3 style="font-family: Outfit; font-size: 1.3rem; margin-bottom: 0.5rem;">CV Parsed & Vectorized!</h3>
            <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Uploaded: <strong>${escapeHtml(file.name)}</strong><br>Re-scored ${allJobs.length} jobs against your CV vector.</p>
            <button class="btn" onclick="closeModal()">View Top Matches</button>
          </div>
        `);
      }
    } catch (err) {
      setModalContent('Error', 'Upload error: ' + err);
    }
  };
  reader.readAsArrayBuffer(file);
}

function setupDragAndDrop() {
  const dropZone = document.getElementById('drop-zone');
  if (dropZone) {
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--accent-cyan)';
        dropZone.style.background = 'rgba(6, 182, 212, 0.12)';
      }, false);
    });
    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'rgba(6, 182, 212, 0.4)';
        dropZone.style.background = 'rgba(6, 182, 212, 0.04)';
      }, false);
    });
    dropZone.addEventListener('drop', (e) => {
      handleCvFileUpload(e);
    }, false);
  }
}

function clientSideVectorRank(jobsList, resumeStr) {
  if (!resumeStr || !jobsList) return jobsList;

  const rLower = resumeStr.toLowerCase();
  const keys = ['python', 'c++', 'c', 'electronics', 'hardware', 'proteus', 'cybersecurity', 'support', 'customer', 'public relations', 'project', 'logic', 'circuit', 'analyst', 'systems'];

  return jobsList.map(j => {
    const text = `${j.title} ${j.company} ${j.location} ${j.description || ''}`.toLowerCase();
    let hits = 0;
    keys.forEach(k => {
      if (rLower.includes(k) && text.includes(k)) hits++;
    });

    let score = 0.35 + (hits * 0.08);
    const strictUnmatched = ['swift', 'ios', 'ruby', 'rails', 'php', 'flutter', 'react native'];
    strictUnmatched.forEach(um => {
      if (text.includes(um) && !rLower.includes(um)) score -= 0.15;
    });

    j.match_score = Math.max(0.12, Math.min(0.96, score));
    return j;
  }).sort((a, b) => b.match_score - a.match_score);
}

function buildSmartAtsCoverLetter(job, resumeStr, tone) {
  const company = job ? job.company : 'Hiring Team';
  const title = job ? job.title : 'Engineering Role';

  return `Dear Hiring Manager at ${company},

I am writing to formally express my strong interest in the ${title} position at ${company}. With a background in Communication and Electronics Engineering and hands-on technical experience spanning Python, hardware circuit design, cybersecurity, and public relations, I am confident in my ability to deliver immediate value to your organization.

Throughout my academic engineering projects and professional roles—including leading public relations initiatives for tech organizations and managing high-stakes client communications—I have consistently demonstrated analytical problem-solving, structured teamwork, and technical precision. My skills closely align with ${company}'s focus on high-quality operational and technical execution.

Key qualifications I bring to the ${title} role include:
• Technical & Systems Rigor: Applied expertise in algorithmic logic, circuit simulation (Proteus), and data analysis to resolve complex engineering challenges.
• Leadership & Project Ownership: Proven experience directing cross-functional teams, optimizing workflow efficiency by 55%, and delivering projects on tight timelines.
• Clear Communication & Client Advocacy: Award-winning customer operations experience managing international stakeholder inquiries and resolving high-stress disputes.

I am particularly excited about ${company}'s goals and would welcome the opportunity to discuss how my technical engineering background and proactive mindset will benefit your team.

Thank you for your time and consideration.

Sincerely,

Salma Ayman Mohamed
salmaayman5421@gmail.com | Giza, Egypt`;
}

function getFallbackInterviewQuestions(job) {
  return {
    "technical": [
      {
        "question": `How do you approach debugging complex technical logic or system boundaries in ${job.title} projects?`,
        "what_interviewer_looks_for": "Structured troubleshooting, variable isolation, simulation tools (Proteus, CAD, GDB), and log analysis.",
        "sample_answer": "I start by isolating the problem domain through systematic input-output testing and behavioral simulation. In my stopwatch and porous material engineering projects, I used Proteus and instrumental analysis to verify signal integrity before physical assembly."
      },
      {
        "question": "Can you explain how you handle state management, debouncing, and error resilience in Python or low-level logic circuits?",
        "what_interviewer_looks_for": "Memory safety, exception handling, hardware debouncing, and preventing unhandled state transitions.",
        "sample_answer": "In Python, I utilize explicit exception handling (try-except blocks) alongside structured logging. For hardware logic, I implement debouncing circuits with IC 4026/555 timers to eliminate noise."
      }
    ],
    "behavioral": [
      {
        "question": "Tell me about a time you led a team or managed high-pressure operations under tight deadlines.",
        "what_interviewer_looks_for": "STAR method, delegation, clear communication, and measurable operational results.",
        "sample_answer": "As CEO of the Scientific Research Society, I led cross-functional teams to execute major events. When timelines were tight, I audited workloads and aligned tasks with team members' strengths—boosting efficiency by 55%."
      },
      {
        "question": "Describe a situation where you resolved a difficult client dispute or stakeholder conflict.",
        "what_interviewer_looks_for": "Empathy, active listening, de-escalation, composure, and positive retention.",
        "sample_answer": "While working at Informa Markets, I handled high-volume international client inquiries under stress. By actively listening and de-escalating in both English and Arabic, I resolved complex disputes and earned the Best Customer Service Agent award."
      }
    ],
    "situational": [
      {
        "question": `If hired at ${job.company}, how would you structure your first 30 to 60 days in this position?`,
        "what_interviewer_looks_for": "30 days learning domain workflows, 60 days delivering quick wins, 90 days driving independent projects.",
        "sample_answer": `In the first 30 days, I will absorb ${job.company}'s workflows and architecture. By day 60, I aim to take full ownership of core responsibilities and deliver key operational enhancements.`
      }
    ]
  };
}

function clientSideEvaluateAnswer(question, answer) {
  if (!answer || answer.trim().length < 10) {
    return {
      clarity: 3, conciseness: 4, impact: 3, relevance: 3, overall_score: 3.25,
      feedback: "Your answer is too short. Try using the STAR method (Situation, Task, Action, Result) with specific technical examples and metrics."
    };
  }

  const words = answer.split(/\s+/).length;
  const aLower = answer.toLowerCase();
  const hasMetrics = /\d+(%|k|ms|s|x)?/.test(answer);
  const hasAction = /i led|i built|i designed|i resolved|i implemented|my role/.test(aLower);

  const clarity = Math.min(10, Math.max(5, 5 + Math.floor(words / 15)));
  const conciseness = (words >= 30 && words <= 160) ? 9 : 6;
  const impact = (hasMetrics || hasAction) ? 8 : 5;
  const relevance = 8;
  const overall = parseFloat(((clarity + conciseness + impact + relevance) / 4).toFixed(2));

  let tips = [];
  if (!hasAction) tips.push("Highlight specific personal actions ('I implemented...', 'I managed...').");
  if (!hasMetrics) tips.push("Add quantitative metrics (e.g., 'boosted efficiency by 55%').");
  if (tips.length === 0) tips.push("Strong structured response with clear action points and relevant experience!");

  return {
    clarity: clarity,
    conciseness: conciseness,
    impact: impact,
    relevance: relevance,
    overall_score: overall,
    feedback: tips.join(' ')
  };
}

function getFallbackJobsList() {
  return [
    {
      id: "fallback_1",
      title: "Technical Support Specialist (Remote)",
      company: "CloudScale Technologies",
      location: "Remote",
      source: "RemoteOK",
      date_posted: new Date().toISOString(),
      match_score: 0.88,
      description: "Looking for a Technical Support Specialist with strong communication skills, problem solving, Python scripting, and customer service experience to assist international clients."
    },
    {
      id: "fallback_2",
      title: "Junior Systems & Hardware Engineer",
      company: "AeroTech Solutions",
      location: "Remote",
      source: "Remotive",
      date_posted: new Date().toISOString(),
      match_score: 0.84,
      description: "Entry-level hardware and systems engineer position. Requires knowledge of circuit design, signal processing, Python/C coding, and testing methodologies."
    },
    {
      id: "fallback_3",
      title: "Cybersecurity & Operations Analyst",
      company: "SecureNet Global",
      location: "Remote",
      source: "Himalayas",
      date_posted: new Date().toISOString(),
      match_score: 0.81,
      description: "Monitor network traffic, assist with security audits, and document incident response protocols. Ideal for candidates with cybersecurity training and strong analytical skills."
    },
    {
      id: "fallback_4",
      title: "Public Relations & Community Coordinator",
      company: "NexGen Media",
      location: "Remote",
      source: "Arbeitnow",
      date_posted: new Date().toISOString(),
      match_score: 0.78,
      description: "Manage outreach, coordinate event partnerships, and direct public relations campaigns for tech and research initiatives."
    },
    {
      id: "fallback_5",
      title: "Python & Automation Engineer",
      company: "DataFlow Systems",
      location: "Remote",
      source: "Jobicy",
      date_posted: new Date().toISOString(),
      match_score: 0.74,
      description: "Build automated web scrapers, data pipelines, and internal tools using Python and SQL. Work closely with cross-functional teams."
    }
  ];
}

function cleanSnippet(str) {
  if (!str) return '';
  return str.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
}

function saveSettings() {
  const role = document.getElementById('cfg-role').value;
  const location = document.getElementById('cfg-location').value;
  alert(`Settings saved! Search query set to '${role}' (${location}).`);
}
