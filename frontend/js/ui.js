/**
 * ui.js — DOM helpers, progress bar, error box, shared state
 */

'use strict';

// ── Shared state (module-level globals) ───────────────────────────────
let _allResults    = [];
let _filtered      = [];
let _currentPage   = 1;
let _currentFilter = 'all';
let _threshold     = 0.50;

// Getters — luôn trả về giá trị mới nhất (tránh lỗi stale closure khi import primitive)
export const getAllResults    = () => _allResults;
export const getFiltered     = () => _filtered;
export const getCurrentPage  = () => _currentPage;
export const getCurrentFilter= () => _currentFilter;
export const getThreshold    = () => _threshold;

// Setters
export function setAllResults(data)  { _allResults    = data; }
export function setFiltered(data)    { _filtered      = data; }
export function setCurrentPage(n)    { _currentPage   = n;   }
export function setCurrentFilter(f)  { _currentFilter = f;   }
export function setThreshold(v)      { _threshold     = v;   }

// ── Progress bar ──────────────────────────────────────────────────────

export function showProgress() {
  document.getElementById('progress-wrap').style.display = 'block';
  document.getElementById('btn-run').disabled = true;
}

export function hideProgress() {
  document.getElementById('progress-wrap').style.display = 'none';
  document.getElementById('btn-run').disabled = false;
}

export function setProgress(pct, msg) {
  document.getElementById('prog-bar').style.width      = pct + '%';
  document.getElementById('prog-pct').textContent      = pct + '%';
  document.getElementById('prog-status').textContent   = msg;
}

// ── Error box ─────────────────────────────────────────────────────────

export function showError(msg) {
  const b = document.getElementById('error-box');
  b.textContent    = msg;
  b.style.display  = 'block';
}

export function hideError() {
  document.getElementById('error-box').style.display = 'none';
}

// ── Time formatter ────────────────────────────────────────────────────

export function formatTime(sec) {
  const m  = Math.floor(sec / 60).toString().padStart(2, '0');
  const s  = Math.floor(sec % 60).toString().padStart(2, '0');
  const ms = Math.floor((sec % 1) * 10);
  return `${m}:${s}.${ms}`;
}
