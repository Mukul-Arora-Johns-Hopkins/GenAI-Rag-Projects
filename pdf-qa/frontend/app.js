/**
 * PDF Q&A Assistant — Frontend
 *
 * Two modes:
 *   LIVE  — connects to a running FastAPI backend (default: localhost:8000)
 *   DEMO — shows simulated answers + real citation formatting for recruiter demos
 *
 * Toggle by setting API_BASE to null/empty (demo) or a real URL (live).
 */
const API_BASE = '';  // empty = demo mode (default for GitHub Pages); set to 'http://localhost:8000' for live
const DEMO_MODE = !API_BASE;

const state = {
  currentFile: null,
  documents: [],
  processing: false,
};

// ── DOM refs ──
const el = {
  ollamaStatus: document.getElementById('ollamaStatus'),
  ollamaText: document.getElementById('ollamaText'),
  docsStatus: document.getElementById('docsStatus'),
  docsCount: document.getElementById('docsCount'),
  modelName: document.getElementById('modelName'),
  demoBanner: document.getElementById('demoBanner'),
  uploadArea: document.getElementById('uploadArea'),
  fileInput: document.getElementById('fileInput'),
  fileInfo: document.getElementById('fileInfo'),
  fileName: document.getElementById('fileName'),
  fileSize: document.getElementById('fileSize'),
  uploadStatus: document.getElementById('uploadStatus'),
  questionInput: document.getElementById('questionInput'),
  askBtn: document.getElementById('askBtn'),
  queryStatus: document.getElementById('queryStatus'),
  answerCard: document.getElementById('answerCard'),
  answerText: document.getElementById('answerText'),
  citationsList: document.getElementById('citationsList'),
  metaTime: document.getElementById('metaTime'),
  metaSources: document.getElementById('metaSources'),
  metaModel: document.getElementById('metaModel'),
};

// ── Init ──
function init() {
  if (DEMO_MODE) {
    el.demoBanner.classList.add('visible');
    el.modelName.textContent = 'llama3.1 (demo)';
    setStatus('ollamaStatus', 'ready');
    el.ollamaText.textContent = 'demo mode';
    setStatus('docsStatus', 'ready');
    el.docsCount.textContent = '0 (demo)';
  } else {
    el.modelName.textContent = '—';
    checkHealth();
  }
}

// ── Health check ──
async function checkHealth() {
  try {
    const r = await fetch(`${API_BASE}/health`);
    const d = await r.json();
    if (d.ollama) {
      setStatus('ollamaStatus', 'ready');
      el.ollamaText.textContent = 'connected';
      el.modelName.textContent = 'llama3.1';
    } else {
      setStatus('ollamaStatus', 'offline');
      el.ollamaText.textContent = 'not reachable';
    }
  } catch {
    setStatus('ollamaStatus', 'offline');
    el.ollamaText.textContent = 'backend offline';
  }
}

// ── Upload handling ──
el.uploadArea.addEventListener('click', () => el.fileInput.click());

el.uploadArea.addEventListener('dragover', (e) => {
  e.preventDefault();
  el.uploadArea.classList.add('dragover');
});

el.uploadArea.addEventListener('dragleave', () => {
  el.uploadArea.classList.remove('dragover');
});

el.uploadArea.addEventListener('drop', (e) => {
  e.preventDefault();
  el.uploadArea.classList.remove('dragover');
  const files = e.dataTransfer.files;
  if (files.length > 0 && files[0].type === 'application/pdf') {
    handleFile(files[0]);
  } else {
    showStatus('uploadStatus', 'Please drop a PDF file.', 'error');
  }
});

el.fileInput.addEventListener('change', () => {
  if (el.fileInput.files.length > 0) {
    handleFile(el.fileInput.files[0]);
  }
});

function handleFile(file) {
  if (!file.name.endsWith('.pdf')) {
    showStatus('uploadStatus', 'Only PDF files are supported.', 'error');
    return;
  }

  state.currentFile = file;
  el.fileName.textContent = file.name;
  el.fileSize.textContent = formatSize(file.size);
  el.fileInfo.classList.add('visible');
  el.uploadArea.style.display = 'none';
  showStatus('uploadStatus', `Processing "${file.name}"…`, 'loading');

  if (DEMO_MODE) {
    // Simulate ingestion delay
    setTimeout(() => {
      showStatus('uploadStatus', `"${file.name}" loaded — 47 chunks indexed (demo).`, 'success');
      setStatus('docsStatus', 'ready');
      el.docsCount.textContent = '1 (demo)';
    }, 1200);
  } else {
    uploadPDF(file);
  }
}

function removeFile() {
  state.currentFile = null;
  el.fileInfo.classList.remove('visible');
  el.uploadArea.style.display = 'block';
  el.fileInput.value = '';
  showStatus('uploadStatus', '', '');
  showStatus('queryStatus', '', '');
  el.answerCard.classList.remove('visible');
  el.answerCard.innerHTML = '';
  if (!DEMO_MODE) {
    fetch(`${API_BASE}/clear`, { method: 'DELETE' }).then(() => {
      setStatus('docsStatus', 'ready');
      el.docsCount.textContent = '0';
    });
  } else {
    setStatus('docsStatus', 'ready');
    el.docsCount.textContent = '0 (demo)';
  }
}

async function uploadPDF(file) {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const r = await fetch(`${API_BASE}/load-pdf`, {
      method: 'POST',
      body: formData,
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Upload failed');
    const d = await r.json();
    showStatus('uploadStatus', `"${d.document}" loaded — ${d.chunks} chunks indexed.`, 'success');
    setStatus('docsStatus', 'ready');
    el.docsCount.textContent = '1';
  } catch (err) {
    showStatus('uploadStatus', err.message || 'Upload failed.', 'error');
  }
}

// ── Ask question ──
async function askQuestion() {
  const question = el.questionInput.value.trim();
  if (!question) return;
  if (state.processing) return;
  state.processing = true;
  el.askBtn.disabled = true;

  if (!state.currentFile && !DEMO_MODE) {
    showStatus('queryStatus', 'Load a PDF first.', 'error');
    state.processing = false;
    el.askBtn.disabled = false;
    return;
  }

  showStatus('queryStatus', 'Thinking…', 'loading');
  el.answerCard.classList.remove('visible');

  if (DEMO_MODE) {
    await simulateAnswer(question);
  } else {
    await queryBackend(question);
  }

  state.processing = false;
  el.askBtn.disabled = false;
}

async function queryBackend(question) {
  try {
    const r = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, top_k: 3, use_hybrid: true }),
    });
    if (!r.ok) {
      const err = await r.json();
      throw new Error(err.detail || 'Query failed');
    }
    const d = await r.json();
    renderAnswer(d);
    showStatus('queryStatus', '', '');
  } catch (err) {
    showStatus('queryStatus', err.message || 'Query failed.', 'error');
  }
}

function renderAnswer(d) {
  el.answerText.innerHTML = renderAnswerHTML(d.answer);
  el.citationsList.innerHTML = d.citations.map(c => `
    <div class="citation">
      <div class="source">${escapeHtml(c.source)}</div>
      <div class="excerpt">${escapeHtml(c.excerpt)}</div>
    </div>
  `).join('');
  el.metaTime.textContent = `⏱ ${d.processing_time_ms}ms`;
  el.metaSources.textContent = `📄 ${d.sources_used} sources`;
  el.metaModel.textContent = 'llama3.1';
  el.answerCard.classList.add('visible');
}

// ── Demo mode simulations ──
const demoAnswers = {
  'main findings': `The study examined the impact of remote work on employee productivity and well-being across a sample of 1,200 knowledge workers over a six-month period.

<strong>Key findings:</strong> The data showed a 13% increase in self-reported productivity among fully remote workers compared to hybrid workers, while fully in-office workers reported a 4% decline. However, this productivity gain came with a measurable trade-off: remote workers reported 22% higher levels of isolation and a 17% decrease in spontaneous collaboration events.

The authors conclude that the optimal arrangement appears to be a structured hybrid model with 2–3 scheduled in-office days focused on collaborative activities, combined with remote days for deep-focus work.`,
  'default': `Based on the document provided, the relevant information addresses your question directly.

The section on methodology describes a mixed-methods approach combining quantitative surveys (n=1,200) with qualitative interviews (n=48). The quantitative analysis used ANOVA to compare productivity metrics across three work arrangement groups, while the qualitative analysis employed thematic coding of interview transcripts.

Results indicate a statistically significant difference in productivity scores between groups (p &lt; 0.01), with post-hoc Tukey tests confirming that the fully remote group outperformed both hybrid and in-office groups on individual task completion metrics.

[ Further details on limitations and future research directions are covered in the discussion section of the document. ]`
};

async function simulateAnswer(question) {
  // Pick a relevant demo answer or fall back
  const q = question.toLowerCase();
  let answer = demoAnswers.default;
  for (const [key, val] of Object.entries(demoAnswers)) {
    if (q.includes(key)) {
      answer = val;
      break;
    }
  }

  // Simulate processing time
  const delay = 800 + Math.random() * 1200;
  await new Promise(r => setTimeout(r, delay));

  renderAnswer({
    answer,
    citations: [
      { source: 'page 3', excerpt: 'The study examined the impact of remote work on employee productivity…' },
      { source: 'page 7', excerpt: 'Results indicate a statistically significant difference in productivity scores…' },
      { source: 'page 12', excerpt: 'The authors conclude that the optimal arrangement appears to be a structured hybrid…' },
    ],
    sources_used: 3,
    processing_time_ms: Math.round(delay),
  });
  showStatus('queryStatus', '', '');
}

// ── Rendering helpers ──
function renderAnswerHTML(text) {
  // Convert markdown-ish bold to HTML
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// ── Status helpers ──
function setStatus(elName, state) {
  const el = document.getElementById(elName === 'ollamaStatus' ? 'ollamaStatus' :
                             elName === 'docsStatus' ? 'docsStatus' : null);
  if (!el) return;
  el.classList.remove('ready', 'busy', 'offline');
  if (state === 'ready') el.classList.add('ready');
  else if (state === 'busy') el.classList.add('busy');
  else if (state === 'offline') el.classList.add('offline');
}

function showStatus(msgElId, text, type) {
  const el = document.getElementById(msgElId);
  el.textContent = text;
  el.classList.remove('visible', 'loading', 'error', 'success');
  if (text) el.classList.add('visible');
  if (type) el.classList.add(type);
}

// ── Clear ──
function clearAll() {
  if (!confirm('Clear all indexed documents? This cannot be undone.')) return;
  removeFile();
}

// ── Keyboard ──
el.questionInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') askQuestion();
});

el.askBtn.addEventListener('click', askQuestion);

// ── Start ──
init();
