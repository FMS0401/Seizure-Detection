/**
 * timeline.js — Vẽ thanh timeline màu theo kết quả seizure/normal
 */

'use strict';

import { formatTime } from './ui.js';

/**
 * Render timeline bar + trục thời gian.
 * @param {Array} windows  — mảng WindowResult từ API
 */
export function renderTimeline(windows) {
  const bar     = document.getElementById('tl-bar');
  const axis    = document.getElementById('tl-axis');
  const tooltip = document.getElementById('tl-tooltip');

  bar.innerHTML = '';
  if (!windows.length) return;

  const total = windows[windows.length - 1].end_sec;

  windows.forEach(w => {
    const seg       = document.createElement('div');
    const widthPct  = (w.end_sec - w.start_sec) / total * 100;
    seg.className   = `tl-seg ${w.label}`;
    seg.style.width = widthPct + '%';

    seg.addEventListener('mousemove', e => {
      tooltip.style.opacity = '1';
      tooltip.style.left    = (e.clientX + 12) + 'px';
      tooltip.style.top     = (e.clientY - 36) + 'px';
      tooltip.innerHTML =
        `#${w.window_idx} &nbsp;|&nbsp; ${w.start_sec}s – ${w.end_sec}s<br>` +
        `<span style="color:${w.label === 'seizure' ? 'var(--seizure)' : 'var(--normal)'}">` +
        `${w.label.toUpperCase()}</span>` +
        ` &nbsp;· prob ${(w.prob * 100).toFixed(1)}%`;
    });
    seg.addEventListener('mouseleave', () => { tooltip.style.opacity = '0'; });

    bar.appendChild(seg);
  });

  // Trục thời gian
  axis.innerHTML  = '';
  const ticks     = Math.min(10, Math.floor(total / 30));
  for (let i = 0; i <= ticks; i++) {
    const t  = Math.round(total * i / ticks);
    const el = document.createElement('span');
    el.textContent = formatTime(t);
    axis.appendChild(el);
  }
}
