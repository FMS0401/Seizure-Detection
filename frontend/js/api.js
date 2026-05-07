/**
 * api.js — Gọi FastAPI backend
 */

'use strict';

// Cùng origin khi deploy; thay bằng 'http://localhost:8000' khi dev local
export const API_BASE = '';

/**
 * Gửi file EDF lên /predict, trả về JSON response.
 * @param {File}   file
 * @param {number} threshold  (0–1) — gửi kèm để backend ghi nhận (tuỳ chọn)
 * @returns {Promise<Object>} PredictionResponse
 */
export async function uploadEDF(file, threshold) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('threshold', threshold);

  const resp = await fetch(`${API_BASE}/predict`, { method: 'POST', body: fd });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(err.detail || 'Lỗi server');
  }

  return resp.json();
}
