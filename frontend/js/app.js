/**
 * app.js — Entry point duy nhất
 */

'use strict';

import {
  getAllResults, getThreshold,
  setAllResults, setThreshold,
  showProgress, hideProgress, setProgress,
  showError, hideError,
  formatTime,
} from './ui.js';

const API = '';   // cùng origin; đổi thành 'http://localhost:8000' khi dev

// ════════════════════════════════════════════════════════════
//  Drop zone
// ════════════════════════════════════════════════════════════
let selectedFile = null;

const dz = document.getElementById('drop-zone');
const fi = document.getElementById('file-input');

dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
fi.addEventListener('change', () => { if (fi.files[0]) setFile(fi.files[0]); });

function setFile(f) {
  if (!f.name.toLowerCase().endsWith('.edf')) {
    showError('Chỉ hỗ trợ file .edf'); return;
  }
  selectedFile = f;
  dz.querySelector('p').textContent = f.name;
  dz.querySelector('small').innerHTML =
    `Kích thước: <strong>${(f.size / 1024 / 1024).toFixed(2)} MB</strong>`;
  document.getElementById('btn-run').disabled = false;
  hideError();
}

// ════════════════════════════════════════════════════════════
//  Threshold slider
// ════════════════════════════════════════════════════════════
const slider = document.getElementById('thresh-slider');
slider.addEventListener('input', () => {
  setThreshold(slider.value / 100);
  document.getElementById('thresh-val').textContent = getThreshold().toFixed(2);
  // Nếu đã có kết quả thì tính lại ngay
  if (getAllResults().length) renderResults(getAllResults());
});

// ════════════════════════════════════════════════════════════
//  Gọi API
// ════════════════════════════════════════════════════════════
async function runAnalysis() {
  if (!selectedFile) return;
  hideError();
  showProgress();

  // Animation progress giả
  let pct = 0, si = 0;
  const stages = [
    [20, 'Đọc & preprocess EDF...'],
    [50, 'Tạo spectrogram...'],
    [80, 'Chạy CNN + LSTM...'],
    [92, 'Tổng hợp kết quả...'],
  ];
  const iv = setInterval(() => {
    if (si < stages.length) {
      const [target, msg] = stages[si];
      if (pct < target) { pct += 2; setProgress(pct, msg); }
      else si++;
    }
  }, 100);

  try {
    const fd = new FormData();
    fd.append('file', selectedFile);
    const resp = await fetch(`${API}/predict`, { method: 'POST', body: fd });
    clearInterval(iv);

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || 'Lỗi server');
    }

    setProgress(100, 'Hoàn thành!');
    await new Promise(r => setTimeout(r, 300));

    const data = await resp.json();
    setAllResults(data.windows);
    renderAll(data);
  } catch (e) {
    clearInterval(iv);
    hideProgress();
    showError('Lỗi: ' + e.message);
  }
}

// Expose cho onclick trong HTML
window.runAnalysis = runAnalysis;

// ════════════════════════════════════════════════════════════
//  Render toàn bộ kết quả
// ════════════════════════════════════════════════════════════
function renderAll(data) {
  hideProgress();
  document.getElementById('result-section').classList.remove('d-none');
  renderSummary(data);
  renderResults(data.windows);
}

// ── Summary cards ─────────────────────────────────────────────────────
function renderSummary(data) {
  const nSeizure = data.windows.filter(w => w.prob >= getThreshold()).length;
  const nNormal  = data.windows.length - nSeizure;
  const pct      = (nSeizure / data.windows.length * 100).toFixed(0);

  document.getElementById('s-total').textContent   = data.windows.length;
  document.getElementById('s-seizure').textContent = nSeizure;
  document.getElementById('s-normal').textContent  = nNormal;
  document.getElementById('s-time').textContent    = (data.processing_ms / 1000).toFixed(1);
  document.getElementById('s-meta').textContent    =
    `File: ${data.filename} · Dài ${data.duration_sec}s · ${data.fs} Hz`;

  // Alert banner
  const alertEl = document.getElementById('result-alert');
  if (nSeizure === 0) {
    alertEl.className = 'alert alert-success mb-3';
    alertEl.innerHTML = '<i class="bi bi-check-circle me-1"></i> Không phát hiện seizure trong bản ghi này.';
  } else {
    alertEl.className = 'alert alert-danger mb-3';
    alertEl.innerHTML =
      `<i class="bi bi-exclamation-triangle me-1"></i>` +
      ` Phát hiện <strong>${nSeizure}</strong> windows có dấu hiệu seizure` +
      ` (${pct}% tổng số windows).`;
  }
}

// ── Áp threshold rồi gọi render timeline + seizure list ───────────────
function renderResults(windows) {
  const thresh = getThreshold();
  // Gán label theo threshold hiện tại
  const tagged = windows.map(w => ({ ...w, label: w.prob >= thresh ? 'seizure' : 'normal' }));
  renderTimeline(tagged);
  renderSeizureEvents(tagged);
  // Cập nhật lại summary cards
  const nS = tagged.filter(w => w.label === 'seizure').length;
  document.getElementById('s-seizure').textContent = nS;
  document.getElementById('s-normal').textContent  = tagged.length - nS;
  const pct = (nS / tagged.length * 100).toFixed(0);
  const alertEl = document.getElementById('result-alert');
  if (nS === 0) {
    alertEl.className = 'alert alert-success mb-3';
    alertEl.innerHTML = '<i class="bi bi-check-circle me-1"></i> Không phát hiện seizure trong bản ghi này.';
  } else {
    alertEl.className = 'alert alert-danger mb-3';
    alertEl.innerHTML =
      `<i class="bi bi-exclamation-triangle me-1"></i>` +
      ` Phát hiện <strong>${nS}</strong> windows có dấu hiệu seizure (${pct}%).`;
  }
}

// ════════════════════════════════════════════════════════════
//  Timeline
// ════════════════════════════════════════════════════════════
function renderTimeline(windows) {
  const bar     = document.getElementById('timeline-bar');
  const axis    = document.getElementById('tl-axis');
  const tooltip = document.getElementById('tl-tooltip');
  bar.innerHTML  = '';
  if (!windows.length) return;

  const total = windows[windows.length - 1].end_sec;

  windows.forEach(w => {
    const seg       = document.createElement('div');
    seg.className   = `tl-seg ${w.label}`;
    seg.style.width = ((w.end_sec - w.start_sec) / total * 100) + '%';

    seg.addEventListener('mousemove', e => {
      tooltip.style.opacity = '1';
      tooltip.style.left    = (e.clientX + 12) + 'px';
      tooltip.style.top     = (e.clientY - 34) + 'px';
      const color = w.label === 'seizure' ? '#ff6b6b' : '#81c995';
      tooltip.innerHTML =
        `${formatTime(w.start_sec)} → ${formatTime(w.end_sec)}&nbsp;&nbsp;` +
        `<span style="color:${color};font-weight:600">${w.label === 'seizure' ? 'SEIZURE' : 'Normal'}</span>` +
        `&nbsp;· ${(w.prob * 100).toFixed(1)}%`;
    });
    seg.addEventListener('mouseleave', () => { tooltip.style.opacity = '0'; });
    bar.appendChild(seg);
  });

  // Trục thời gian
  axis.innerHTML = '';
  const ticks = Math.min(8, Math.floor(total / 30));
  for (let i = 0; i <= ticks; i++) {
    const el = document.createElement('span');
    el.textContent = formatTime(Math.round(total * i / ticks));
    axis.appendChild(el);
  }
}

// ════════════════════════════════════════════════════════════
//  Seizure events — gộp các windows seizure liền kề
// ════════════════════════════════════════════════════════════
function groupSeizureWindows(windows) {
  // Gộp các window liền kề cùng label=seizure thành 1 event
  const events = [];
  let current  = null;
  for (const w of windows) {
    if (w.label === 'seizure') {
      if (!current) {
        current = { start: w.start_sec, end: w.end_sec, probs: [w.prob] };
      } else if (w.start_sec <= current.end + 4) {
        // Khoảng cách ≤ 1 window thì coi là liền kề
        current.end = Math.max(current.end, w.end_sec);
        current.probs.push(w.prob);
      } else {
        events.push(current);
        current = { start: w.start_sec, end: w.end_sec, probs: [w.prob] };
      }
    } else {
      if (current) { events.push(current); current = null; }
    }
  }
  if (current) events.push(current);
  return events;
}

function renderSeizureEvents(windows) {
  const events  = groupSeizureWindows(windows);
  const tbody   = document.getElementById('seizure-tbody');
  const noMsg   = document.getElementById('no-seizure-msg');
  const footer  = document.getElementById('seizure-footer');
  const table   = document.getElementById('seizure-table');

  tbody.innerHTML = '';

  if (events.length === 0) {
    table.classList.add('d-none');
    noMsg.classList.remove('d-none');
    footer.textContent = '';
    return;
  }

  table.classList.remove('d-none');
  noMsg.classList.add('d-none');

  events.forEach((ev, i) => {
    const avgProb = ev.probs.reduce((a, b) => a + b, 0) / ev.probs.length;
    const dur     = (ev.end - ev.start).toFixed(0);
    const tr      = document.createElement('tr');
    tr.className  = 'seizure-row';
    tr.innerHTML  = `
      <td><span class="badge text-bg-danger">${i + 1}</span></td>
      <td>${formatTime(ev.start)}</td>
      <td>${formatTime(ev.end)}</td>
      <td>${dur} giây</td>
      <td>
        <div class="d-flex align-items-center gap-2">
          <div class="progress flex-grow-1" style="height:6px">
            <div class="progress-bar bg-danger" style="width:${(avgProb*100).toFixed(0)}%"></div>
          </div>
          <span class="text-danger fw-semibold small">${(avgProb*100).toFixed(1)}%</span>
        </div>
      </td>`;
    tbody.appendChild(tr);
  });

  const totalSec = events.reduce((sum, ev) => sum + (ev.end - ev.start), 0);
  footer.textContent =
    `Tổng cộng ${events.length} đoạn seizure · khoảng ${totalSec.toFixed(0)} giây bị ảnh hưởng`;
}
