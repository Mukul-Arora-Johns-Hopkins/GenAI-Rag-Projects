/**
 * YouTube Research Assistant — Frontend
 *
 * Two modes:
 *   LIVE  — connects to a running FastAPI backend (default: localhost:8001)
 *   DEMO — shows simulated transcripts + real citation formatting for recruiter demos
 *
 * Toggle by setting API_BASE to null/empty (demo) or a real URL (live).
 */
const API_BASE = '';  // empty = demo mode (default for GitHub Pages); set to 'http://localhost:8001' for live
const DEMO_MODE = !API_BASE;

const state = {
  currentVideo: null,
  processing: false,
};

// ── DOM refs ──
const el = {
  ollamaStatus: document.getElementById('ollamaStatus'),
  ollamaText: document.getElementById('ollamaText'),
  videoStatus: document.getElementById('videoStatus'),
  videoCount: document.getElementById('videoCount'),
  modelName: document.getElementById('modelName'),
  demoBanner: document.getElementById('demoBanner'),
  urlInput: document.getElementById('urlInput'),
  addBtn: document.getElementById('addBtn'),
  addStatus: document.getElementById('addStatus'),
  videoInfo: document.getElementById('videoInfo'),
  videoTitle: document.getElementById('videoTitle'),
  videoDuration: document.getElementById('videoDuration'),
  videoTranscriptLength: document.getElementById('videoTranscriptLength'),
  videoChunks: document.getElementById('videoChunks'),
  timelineViz: document.getElementById('timelineViz'),
  timelineMarkers: document.getElementById('timelineMarkers'),
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
    setStatus('videoStatus', 'ready');
    el.videoCount.textContent = '0 (demo)';
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

// ── Add video ──
el.addBtn.addEventListener('click', addVideo);
el.urlInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') addVideo();
});

async function addVideo() {
  const url = el.urlInput.value.trim();
  if (!url) return;

  // Extract video ID
  const videoId = extractVideoId(url);
  if (!videoId) {
    showStatus('addStatus', 'Invalid YouTube URL. Use a standard youtube.com/watch?v=... link.', 'error');
    return;
  }

  state.currentVideo = { url, videoId };
  el.urlInput.value = '';
  el.addBtn.disabled = true;

  showStatus('addStatus', 'Fetching transcript…', 'loading');

  if (DEMO_MODE) {
    // Simulate fetching + indexing
    const delay = 1500 + Math.random() * 1000;
    await new Promise(r => setTimeout(r, delay));
    simulateVideoLoaded(videoId);
  } else {
    await processVideo(url, videoId);
  }

  el.addBtn.disabled = false;
}

function extractVideoId(url) {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([^&?\/\s]+)/,
    /^([a-zA-Z0-9_-]{11})$/,
  ];
  for (const p of patterns) {
    const m = url.match(p);
    if (m) return m[1];
  }
  return null;
}

async function processVideo(url, videoId) {
  try {
    const r = await fetch(`${API_BASE}/process-video`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || 'Failed to process video');
    const d = await r.json();

    showStatus('addStatus', `"${d.title}" — transcript loaded, ${d.chunks} chunks indexed.`, 'success');
    setStatus('videoStatus', 'ready');
    el.videoCount.textContent = '1';

    el.videoTitle.textContent = d.title;
    el.videoDuration.textContent = `⏱ ${d.duration}`;
    el.videoTranscriptLength.textContent = `📝 ${d.transcript_length} chars`;
    el.videoChunks.textContent = `🧩 ${d.chunks} chunks`;
    el.videoInfo.classList.add('visible');
    el.currentVideo = { title: d.title, videoId, duration: d.duration, transcriptLength: d.transcript_length, chunks: d.chunks };
  } catch (err) {
    showStatus('addStatus', err.message || 'Failed to process video.', 'error');
    el.addBtn.disabled = false;
  }
}

function simulateVideoLoaded(videoId) {
  const titles = [
    'The Future of AI in Scientific Research',
    'Understanding Large Language Models: A Deep Dive',
    'Introduction to Retrieval-Augmented Generation',
    'How Neural Networks Learn Representations',
    'A Practical Guide to Building RAG Systems',
  ];
  const title = titles[Math.floor(Math.random() * titles.length)];

  el.videoTitle.textContent = title;
  el.videoDuration.textContent = '⏱ 24:36';
  el.videoTranscriptLength.textContent = '📝 38,420 chars';
  el.videoChunks.textContent = '🧩 52 chunks';
  el.videoInfo.classList.add('visible');
  el.currentVideo = { title, videoId, duration: '24:36', transcriptLength: 38420, chunks: 52 };

  setStatus('videoStatus', 'ready');
  el.videoCount.textContent = '1';

  // Draw timeline
  drawTimeline(videoId);

  showStatus('addStatus', `"${title}" — transcript loaded, 52 chunks indexed (demo).`, 'success');
}

// ── Timeline visualization ──
function drawTimeline(videoId) {
  el.timelineViz.classList.add('visible');
  const markersContainer = el.timelineMarkers;
  markersContainer.innerHTML = '';

  // Create 8 markers across the timeline
  const numMarkers = 8;
  for (let i = 0; i < numMarkers; i++) {
    const pct = ((i + 1) / numMarkers) * 100;
    const time = formatTime((i + 1) * 24.36 / numMarkers);

    const marker = document.createElement('div');
    marker.className = 'timeline-marker';
    marker.style.left = pct + '%';
    marker.title = time;

    const tooltip = document.createElement('div');
    tooltip.className = 'tl-tooltip';
    tooltip.textContent = time;
    marker.appendChild(tooltip);

    marker.addEventListener('click', () => {
      document.querySelectorAll('.timeline-marker').forEach(m => m.classList.remove('active'));
      marker.classList.add('active');
      showStatus('queryStatus', `Jumped to ${time} in transcript.`, 'loading');
      setTimeout(() => showStatus('queryStatus', '', ''), 2000);
    });

    markersContainer.appendChild(marker);
  }
}

function formatTime(minutes) {
  const m = Math.floor(minutes);
  const s = Math.round((minutes - m) * 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Remove video ──
function removeVideo() {
  state.currentVideo = null;
  el.videoInfo.classList.remove('visible');
  el.timelineViz.classList.remove('visible');
  el.timelineMarkers.innerHTML = '';
  el.answerCard.classList.remove('visible');
  el.answerCard.innerHTML = '';
  showStatus('addStatus', '', '');
  showStatus('queryStatus', '', '');
  if (!DEMO_MODE) {
    fetch(`${API_BASE}/clear`, { method: 'DELETE' }).then(() => {
      setStatus('videoStatus', 'ready');
      el.videoCount.textContent = '0';
    });
  } else {
    setStatus('videoStatus', 'ready');
    el.videoCount.textContent = '0 (demo)';
  }
}

// ── Ask question ──
async function askQuestion() {
  const question = el.questionInput.value.trim();
  if (!question) return;
  if (state.processing) return;
  if (!state.currentVideo && !DEMO_MODE) {
    showStatus('queryStatus', 'Add a video first.', 'error');
    return;
  }

  state.processing = true;
  el.askBtn.disabled = true;
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
      body: JSON.stringify({ question, top_k: 3 }),
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
  'ai': `The speaker argues that AI is transitioning from a tool that augments human capability to a partner that can independently drive parts of the research process.

<strong>Three phases are described:</strong>

1. <strong>Augmentation (current):</strong> AI assists with literature review, data cleaning, and initial analysis. Researchers remain in control of hypothesis formation and interpretation.

2. <strong>Collaboration (near-term):</strong> AI systems will propose hypotheses, design experiments, and suggest analytical approaches. The researcher's role shifts toward framing the right questions and validating outputs.

3. <strong>Autonomy (longer-term):</strong> Self-driving labs and AI-only research pipelines will handle end-to-end cycles for well-defined problems, with human oversight focused on goal-setting and ethical review.

The speaker cautions that this progression is uneven across domains — fields with rich structured data (computational biology, materials science) will move faster than those requiring physical experimentation or nuanced qualitative judgment.`,
  'default': `The relevant section of the transcript addresses your question directly.

The speaker explains that the core challenge is not the availability of data or compute, but the <strong>alignment between what we ask and what we can evaluate</strong>. As systems become more capable, our ability to verify their outputs does not scale at the same rate.

Three practical recommendations emerge from the discussion:

1. <strong>Invest in evaluation infrastructure</strong> — build robust test suites and benchmark datasets before deploying systems in production.
2. <strong>Design for observability</strong> — log intermediate states, reasoning traces, and decision points so that failures are diagnosable.
3. <strong>Keep humans in the loop for high-stakes decisions</strong> — automation is valuable, but the cost of error in critical applications demands human judgment as a final check.

The speaker concludes that the most successful deployments pair strong automation with strong verification, rather than pursuing full autonomy prematurely.`
};

async function simulateAnswer(question) {
  const q = question.toLowerCase();
  let answer = demoAnswers.default;
  for (const [key, val] of Object.entries(demoAnswers)) {
    if (q.includes(key)) {
      answer = val;
      break;
    }
  }

  const delay = 900 + Math.random() * 1100;
  await new Promise(r => setTimeout(r, delay));

  renderAnswer({
    answer,
    citations: [
      { source: '02:14', excerpt: 'The speaker argues that AI is transitioning from a tool that augments human capability…' },
      { source: '08:42', excerpt: 'Three phases are described: Augmentation, Collaboration, and Autonomy…' },
      { source: '15:28', excerpt: 'The speaker cautions that this progression is uneven across domains…' },
    ],
    sources_used: 3,
    processing_time_ms: Math.round(delay),
  });
  showStatus('queryStatus', '', '');
}

// ── Rendering helpers ──
function renderAnswerHTML(text) {
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

// ── Status helpers ──
function setStatus(elName, state) {
  const elMap = { ollamaStatus: 'ollamaStatus', videoStatus: 'videoStatus' };
  const el = document.getElementById(elMap[elName]);
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
  if (!confirm('Clear all processed videos? This cannot be undone.')) return;
  removeVideo();
}

// ── Keyboard ──
el.questionInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') askQuestion();
});
