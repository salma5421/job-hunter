let allJobs = [];

document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  loadJobs();
  loadResume();
});

async function loadStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('stat-total-jobs').innerText = data.total_jobs || 0;
    document.getElementById('stat-top-matches').innerText = data.top_matches || 0;
    document.getElementById('stat-letters').innerText = data.total_letters || 0;
    document.getElementById('stat-resume-status').innerText = data.resume_present ? 'Active' : 'Missing';
  } catch (e) {
    console.error('Failed to load status:', e);
  }
}

async function loadJobs() {
  const minScore = document.getElementById('score-filter').value;
  const container = document.getElementById('jobs-container');
  container.innerHTML = '<div style="text-align:center; padding: 3rem; color: var(--text-dim);">Loading matched job opportunities...</div>';

  try {
    const res = await fetch(`/api/jobs?min_score=${minScore}`);
    const data = await res.json();
    allJobs = data.jobs || [];
    renderJobs(allJobs);
  } catch (e) {
    container.innerHTML = '<div style="text-align:center; color: var(--accent-pink);">Failed to connect to backend server.</div>';
  }
}

function renderJobs(jobs) {
  const container = document.getElementById('jobs-container');
  if (!jobs || jobs.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 4rem; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-glass);">
        <h3 style="font-family: Outfit; font-size: 1.4rem; margin-bottom: 0.5rem;">No job matches found for this filter</h3>
        <p style="color: var(--text-muted); margin-bottom: 1.5rem;">Click "Run 130+ Scanner" above to scrape fresh roles from top tech career pages!</p>
        <button class="btn" onclick="triggerScan()">⚡ Run Job Scanner Now</button>
      </div>
    `;
    return;
  }

  container.innerHTML = jobs.map(job => {
    const score = (job.match_score || 0);
    const scorePct = Math.round(score * 100);
    let badgeClass = 'score-low';
    if (score >= 0.80) badgeClass = 'score-high';
    else if (score >= 0.70) badgeClass = 'score-mid';

    return `
      <div class="job-card">
        <div class="job-info">
          <div class="job-title-row">
            <a href="${job.url}" target="_blank" class="job-title">${escapeHtml(job.title)}</a>
            <span class="badge-score ${badgeClass}">🎯 Match Score: ${scorePct}%</span>
            <span style="font-size: 0.8rem; background: rgba(255,255,255,0.06); padding: 0.2rem 0.6rem; border-radius: 4px; color: var(--text-muted);">
              ${escapeHtml(job.source)}
            </span>
          </div>
          <div class="job-meta">
            <span>🏢 <strong>${escapeHtml(job.company)}</strong></span>
            <span>📍 ${escapeHtml(job.location)}</span>
            <span>📅 Scraped: ${new Date(job.date_scraped).toLocaleDateString()}</span>
          </div>
          <div class="job-desc">${escapeHtml(job.description || 'No description preview available.')}</div>
        </div>
        <div class="job-actions">
          <button class="btn btn-purple" onclick="generateLetter('${job.id}')">
            <span>✉️</span> Draft Cover Letter
          </button>
          <button class="btn btn-secondary" onclick="startInterviewPrep('${job.id}')">
            <span>🎤</span> Mock Interview
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function filterJobs() {
  const query = document.getElementById('search-input').value.toLowerCase();
  const minScore = parseFloat(document.getElementById('score-filter').value);

  const filtered = allJobs.filter(job => {
    const matchesQuery = job.title.toLowerCase().includes(query) ||
                         job.company.toLowerCase().includes(query) ||
                         job.description.toLowerCase().includes(query);
    const matchesScore = (job.match_score || 0) >= minScore;
    return matchesQuery && matchesScore;
  });

  renderJobs(filtered);
}

async function triggerScan() {
  const btn = document.getElementById('btn-scan');
  btn.innerText = '⌛ Scanning 130+ sites...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ search_term: 'software engineer' })
    });
    const data = await res.json();
    alert(`✅ Job Scrape Complete!\nTotal Scraped: ${data.total_scraped}\nNew Jobs Added: ${data.new_jobs_added}`);
    loadStatus();
    loadJobs();
  } catch (e) {
    alert('Failed to run scraper: ' + e);
  } finally {
    btn.innerHTML = '<span>⚡</span> Run 130+ Scanner';
    btn.disabled = false;
  }
}

async function triggerReMatch() {
  const btn = document.getElementById('btn-re-rank');
  btn.innerText = '⌛ Scoring...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ min_score: 0.0 })
    });
    const data = await res.json();
    alert(`🎯 Vector matching complete! Re-scored ${data.count} jobs against current resume.`);
    loadStatus();
    loadJobs();
  } catch (e) {
    alert('Re-rank failed: ' + e);
  } finally {
    btn.innerHTML = '<span>🎯</span> Re-Rank Vector Match';
    btn.disabled = false;
  }
}

async function loadResume() {
  try {
    const res = await fetch('/api/resume');
    const data = await res.json();
    document.getElementById('resume-textarea').value = data.resume || '';
  } catch (e) {
    console.error('Failed to load resume:', e);
  }
}

async function saveResume() {
  const text = document.getElementById('resume-textarea').value;
  const btn = document.getElementById('btn-save-resume');
  btn.innerText = 'Saving & Vectorizing...';

  try {
    const res = await fetch('/api/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume: text })
    });
    const data = await res.json();
    alert('✅ Resume updated! Jobs automatically re-ranked against updated resume vector.');
    loadStatus();
    loadJobs();
  } catch (e) {
    alert('Save failed: ' + e);
  } finally {
    btn.innerHTML = '<span>💾</span> Save & Re-index Embeddings';
  }
}

async function generateLetter(jobId) {
  openModal('Drafting Tailored Cover Letter...', '<div style="padding: 2rem; text-align: center;">🤖 AI is generating cover letter...</div>');

  try {
    const res = await fetch('/api/cover_letter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId })
    });
    const data = await res.json();

    const letterHtml = `
      <div style="white-space: pre-wrap; font-family: monospace; background: rgba(0,0,0,0.5); padding: 1.5rem; border-radius: var(--radius-md); border: 1px solid var(--border-glass); line-height: 1.6;">${escapeHtml(data.cover_letter)}</div>
      <div style="margin-top: 1rem; display: flex; justify-content: flex-end; gap: 1rem;">
        <button class="btn btn-secondary" onclick="navigator.clipboard.writeText(\`${escapeJs(data.cover_letter)}\`); alert('Copied to clipboard!');">📋 Copy Letter</button>
      </div>
    `;
    setModalContent('Tailored Cover Letter Draft', letterHtml);
    loadStatus();
  } catch (e) {
    setModalContent('Error', 'Failed to generate cover letter: ' + e);
  }
}

async function startInterviewPrep(jobId) {
  openModal('Preparing AI Mock Interview...', '<div style="padding: 2rem; text-align: center;">🤖 Generating targeted interview questions...</div>');

  try {
    const res = await fetch('/api/interview/questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId })
    });
    const questionsData = await res.json();

    let html = '<div style="display: flex; flex-direction: column; gap: 1.5rem;">';
    
    ['technical', 'behavioral', 'situational'].forEach(cat => {
      if (questionsData[cat] && questionsData[cat].length > 0) {
        html += `<h3 style="font-family: Outfit; color: var(--accent-cyan); text-transform: capitalize;">${cat} Questions</h3>`;
        questionsData[cat].forEach((qObj, idx) => {
          const qId = `${cat}_${idx}`;
          const sampleAns = qObj.sample_answer ? escapeHtml(qObj.sample_answer) : '';
          html += `
            <div class="qa-card">
              <div class="qa-question">Q${idx + 1}: ${escapeHtml(qObj.question)}</div>
              <div class="qa-hint">💡 What interviewer looks for: ${escapeHtml(qObj.what_interviewer_looks_for)}</div>
              <textarea id="ans_${qId}" rows="3" placeholder="Type your mock answer here to be evaluated by AI..."></textarea>
              <div style="margin-top: 0.5rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                <button class="btn btn-secondary" onclick="evaluateAnswer('${qId}', \`${escapeJs(qObj.question)}\`)">Submit for AI Grade</button>
                ${sampleAns ? `<button class="btn btn-secondary" style="border-color: var(--accent-purple);" onclick="toggleSampleAnswer('${qId}')">💡 View Model Answer</button>` : ''}
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

    setModalContent('AI Mock Interview Questions & Feedback', html);
  } catch (e) {
    setModalContent('Error', 'Failed to generate interview questions: ' + e);
  }
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
    const evalData = await res.json();

    resultDiv.innerHTML = `
      <div class="scorecard">
        <div class="scorecard-metrics">
          <div class="score-chip">Overall: ${evalData.overall_score}/10</div>
          <div class="score-chip">Clarity: ${evalData.clarity}/10</div>
          <div class="score-chip">Conciseness: ${evalData.conciseness}/10</div>
          <div class="score-chip">Impact: ${evalData.impact}/10</div>
        </div>
        <div style="font-size: 0.9rem; color: var(--text-main); line-height: 1.5;">${escapeHtml(evalData.feedback)}</div>
      </div>
    `;
  } catch (e) {
    resultDiv.innerHTML = '<div style="color: var(--accent-pink);">Evaluation error.</div>';
  }
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

  document.getElementById(`tab-btn-${tabId}`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.add('active');
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

      const res = await fetch('/api/upload_cv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          file_b64: base64String
        })
      });
      const data = await res.json();
      if (data.success) {
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
        setModalContent('Error', 'Failed to parse CV: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      setModalContent('Error', 'Upload failed: ' + err);
    }
  };
  reader.readAsArrayBuffer(file);
}

// Drag and drop zone handlers
document.addEventListener('DOMContentLoaded', () => {
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
});

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeJs(str) {
  if (!str) return '';
  return String(str).replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
}

