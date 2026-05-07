/**
 * app.js — Entry point: kết nối upload, threshold, runAnalysis, renderAll
 */

'use strict';

import { uploadEDF }                           from './api.js';
import {
  getAllResults, getThreshold,
  setAllResults, setThreshold,
  showProgress, hideProgress, setProgress,
  showError, hideError,
}                                              from './ui.js';
import { renderTimeline }                      from './timeline.js';
import { setFilter }                           from './table.js';

// Expose functions called from inline onclick attributes in HTML
window.runAnalysis = runAnalysis;
window.setFilter   = setFilter;

// ── Drop zone ─────────────────────────────────────────────────────────

let selectedFile = null;

const dz = document.getElementById('drop-zone');
const fi = document.getElementById('file-input');

dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('drag-over'); });
dz.addEventListener('dragleave', ()  => dz.classList.remove('drag-over'));
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) _setFile(f);
});
fi.addEventListener('change', () => { if (fi.files[0]) _setFile(fi.files[0]); });

function _setFile(f) {
  if (!f.name.toLowerCase().endsWith('.edf')) {
    showError('Chỉ hỗ trợ file .edf');
    return;
  }
  selectedFile = f;
  dz.querySelector('.upload-title').textContent = f.name;
  dz.querySelector('.upload-sub').innerHTML =
    `Kích thước: <strong>${(f.size / 1024 / 1024).toFixed(2)} MB</strong>`;
  document.getElementById('btn-run').disabled = false;
  hideError();
}

// ── Threshold slider ──────────────────────────────────────────────────

const slider = document.getElementById('thresh-slider');
slider.addEventListener('input', () => {
  setThreshold(slider.value / 100);
  document.getElementById('thresh-val').textContent = getThreshold().toFixed(2);
  if (getAllResults().length) _recomputeAndRender();
});

function _recomputeAndRender() {
  const results   = getAllResults();
  const threshold = getThreshold();
  results.forEach(w => {
    w.label = w.prob >= threshold ? 'seizure' : 'normal';
  });
  const nSeizure = results.filter(w => w.label === 'seizure').length;
  const sp       = (nSeizure / results.length * 100).toFixed(1);

  document.getElementById('s-seizure').textContent     = nSeizure;
  document.getElementById('s-normal').textContent      = results.length - nSeizure;
  document.getElementById('s-seizure-pct').textContent = sp + '% windows';
  document.getElementById('s-normal-pct').textContent  = (100 - parseFloat(sp)).toFixed(1) + '% windows';

  renderTimeline(results);
  setFilter('all');        // re-render table with current filter
}

// ── Main analysis flow ────────────────────────────────────────────────

async function runAnalysis() {
  if (!selectedFile) return;

  hideError();
  showProgress();

  // Fake progress animation
  let pct = 0, si = 0;
  const stages = [
    [20, 'Đọc & preprocess EDF...'],
    [45, 'Tạo spectrogram từng window...'],
    [75, 'Chạy CNN + LSTM inference...'],
    [90, 'Tổng hợp kết quả...'],
  ];
  const iv = setInterval(() => {
    if (si < stages.length) {
      const [target, msg] = stages[si];
      if (pct < target) { pct += 2; setProgress(pct, msg); }
      else si++;
    }
  }, 120);

  try {
    const data = await uploadEDF(selectedFile, getThreshold());

    clearInterval(iv);
    setProgress(100, 'Hoàn thành!');
    await new Promise(r => setTimeout(r, 400));

    setAllResults(data.windows);
    _renderAll(data);
  } catch (e) {
    clearInterval(iv);
    hideProgress();
    showError('❌ ' + e.message);
  }
};

// ── Render summary + timeline + table ────────────────────────────────

function _renderAll(data) {
  hideProgress();

  // Summary cards
  document.getElementById('s-total').textContent   = data.n_windows;
  document.getElementById('s-seizure').textContent = data.n_seizure;
  document.getElementById('s-normal').textContent  = data.n_normal;
  document.getElementById('s-dur').textContent     = `Dài ${data.duration_sec}s · ${data.fs}Hz`;
  document.getElementById('s-time').textContent    = (data.processing_ms / 1000).toFixed(1);

  const sp = (data.n_seizure / data.n_windows * 100).toFixed(1);
  document.getElementById('s-seizure-pct').textContent = sp + '% windows';
  document.getElementById('s-normal-pct').textContent  = (100 - parseFloat(sp)).toFixed(1) + '% windows';

  const summary = document.getElementById('summary');
  summary.style.display = 'block';
  summary.classList.add('fade-up');

  // Timeline
  renderTimeline(data.windows);
  const tl = document.getElementById('timeline-section');
  tl.style.display = 'block';
  tl.classList.add('fade-up');

  // Table
  setFilter('all');
}
