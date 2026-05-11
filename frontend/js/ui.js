/**
 * ui.js — Shared state + DOM helpers
 */

'use strict';

// ── State ─────────────────────────────────────────────────────────────
let _allResults = [];
let _threshold  = 0.20;

export const getAllResults = () => _allResults;
export const getThreshold = () => _threshold;
export function setAllResults(data) { _allResults = data; }
export function setThreshold(v)     { _threshold  = v;    }

// ── Progress ──────────────────────────────────────────────────────────
export function showProgress() {
  document.getElementById('progress-wrap').classList.remove('d-none');
  document.getElementById('btn-run').disabled = true;
}
export function hideProgress() {
  document.getElementById('progress-wrap').classList.add('d-none');
  document.getElementById('btn-run').disabled = false;
}
export function setProgress(pct, msg) {
  document.getElementById('prog-bar').style.width    = pct + '%';
  document.getElementById('prog-pct').textContent    = pct + '%';
  document.getElementById('prog-status').textContent = msg;
}

// ── Error ─────────────────────────────────────────────────────────────
export function showError(msg) {
  const b = document.getElementById('error-box');
  b.textContent = msg;
  b.classList.remove('d-none');
}
export function hideError() {
  document.getElementById('error-box').classList.add('d-none');
}

// ── Format time mm:ss ─────────────────────────────────────────────────
export function formatTime(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, '0');
  const s = Math.floor(sec % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}
