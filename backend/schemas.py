"""
schemas.py — Pydantic request/response models
"""
from pydantic import BaseModel
from typing import List


class WindowResult(BaseModel):
    window_idx:  int
    start_sec:   float
    end_sec:     float
    label:       str
    prob:        float


class PredictionResponse(BaseModel):
    filename:      str
    duration_sec:  float
    fs:            int
    n_windows:     int
    n_seizure:     int
    n_normal:      int
    windows:       List[WindowResult]
    processing_ms: int
