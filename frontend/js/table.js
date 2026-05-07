/**
 * table.js — Bảng kết quả, filter (All / Seizure / Normal), phân trang
 */

'use strict';

import {
  getAllResults, getFiltered, getCurrentPage,
  setFiltered, setCurrentPage, setCurrentFilter,
  formatTime,
} from './ui.js';

const PAGE_SIZE = 20;

// ── Filter ────────────────────────────────────────────────────────────

export function setFilter(f) {
  setCurrentFilter(f);
  setCurrentPage(1);

  ['all', 'seizure', 'normal'].forEach(k => {
    document.getElementById('fb-' + k).className =
      'filter-btn' + (k === f ? ` active-${k}` : '');
  });

  setFiltered(f === 'all' ? getAllResults() : getAllResults().filter(w => w.label === f));
  renderPage();
}

// ── Table rows ────────────────────────────────────────────────────────

export function renderPage() {
  const tbody = document.getElementById('results-tbody');
  tbody.innerHTML = '';

  const page = getFiltered().slice(
    (getCurrentPage() - 1) * PAGE_SIZE,
    getCurrentPage() * PAGE_SIZE
  );

  page.forEach(w => {
    const tr = document.createElement('tr');
    if (w.label === 'seizure') tr.classList.add('row-seizure');

    tr.innerHTML = `
      <td class="win-idx">${w.window_idx}</td>
      <td class="win-time">${formatTime(w.start_sec)}</td>
      <td class="win-time">${formatTime(w.start_sec)} → ${formatTime(w.end_sec)}</td>
      <td>
        <span class="chip ${w.label}">
          ${w.label === 'seizure' ? 'SEIZURE' : 'NORMAL'}
        </span>
      </td>
      <td>
        <div class="prob-cell">
          <div class="prob-bar-bg">
            <div class="prob-bar-fill ${w.label}"
                 style="width:${(w.prob * 100).toFixed(1)}%"></div>
          </div>
          <span class="prob-num">${(w.prob * 100).toFixed(1)}%</span>
        </div>
      </td>`;

    tbody.appendChild(tr);
  });

  renderPagination();
}

// ── Pagination ────────────────────────────────────────────────────────

function renderPagination() {
  const total = Math.ceil(getFiltered().length / PAGE_SIZE);
  const pg    = document.getElementById('pagination');
  pg.innerHTML = '';
  if (total <= 1) return;

  const addBtn = (label, page, disabled, active) => {
    const b        = document.createElement('button');
    b.className    = 'page-btn' + (active ? ' active' : '');
    b.textContent  = label;
    b.disabled     = disabled;
    if (!disabled) b.onclick = () => { setCurrentPage(page); renderPage(); };
    pg.appendChild(b);
  };

  const cp    = getCurrentPage();
  addBtn('‹', cp - 1, cp === 1);

  const start = Math.max(1, cp - 2);
  const end   = Math.min(total, cp + 2);
  for (let p = start; p <= end; p++) {
    addBtn(p, p, false, p === cp);
  }

  addBtn('›', cp + 1, cp === total);
}
