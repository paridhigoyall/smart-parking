"""
Smoke/fire detection via classical color-space heuristics (OpenCV), not a
trained neural network. This is a real, structurally-correct baseline
technique from the pre-deep-learning fire-detection literature — fire
pixels cluster in a fairly specific R>G>B, high-saturation warm-color
region; smoke pixels are comparatively desaturated, greyish, and diffuse
over a large area — but it's honest to be upfront about its limits: it
will false-positive on things that share those color signatures (sunset
lighting for "fire", fog/haze/dust for "smoke") and won't catch fires or
smoke with atypical coloring. A trained CNN (or even a lightweight
color+motion+texture ensemble) is the right production upgrade; this is a
genuine, working, but deliberately simple baseline suitable for a
prototype, not a validated safety-critical detector on its own — treat a
positive result here as "worth a human looking at the camera," the same
spirit as every other risk signal in this platform, not as a substitute
for the gas sensors that are the platform's primary safety signal.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np

# Fraction of frame pixels matching the fire/smoke color profile before
# we call it a detection, chosen so a lighter or small localized source
# still triggers without flagging on scattered noise pixels.
FIRE_AREA_THRESHOLD = 0.015
FIRE_AREA_SATURATED = 0.08  # ratio considered "fully confident"
SMOKE_AREA_THRESHOLD = 0.28
SMOKE_AREA_SATURATED = 0.55
# Smoke has a soft, non-zero local gradient (it's translucent and diffuse);
# flat painted surfaces, pavement, and clear sky have near-zero local
# variance, and gravel/foliage/crowds have far higher variance than smoke.
# This band is what keeps a grey car or an overcast sky from reading as
# "smoke" under color thresholds alone.
SMOKE_TEXTURE_MIN = 3.0
SMOKE_TEXTURE_MAX = 22.0


@dataclass
class SmokeFireResult:
    fire_detected: bool
    fire_confidence: float
    fire_area_ratio: float
    smoke_detected: bool
    smoke_confidence: float
    smoke_area_ratio: float


class SmokeFireDetector:
    def analyze(self, image_bytes: bytes) -> SmokeFireResult:
        array = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Could not decode image")

        total_pixels = bgr.shape[0] * bgr.shape[1]
        b, g, r = bgr[:, :, 0].astype(int), bgr[:, :, 1].astype(int), bgr[:, :, 2].astype(int)
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1].astype(int), hsv[:, :, 2].astype(int)

        # --- Fire: warm, saturated, R > G > B ---------------------------
        fire_mask = (r > 190) & (g > 90) & (g < 220) & (b < 140) & (r > g) & (g >= b) & (s > 80)
        fire_ratio = float(fire_mask.sum()) / total_pixels

        # --- Smoke: desaturated, greyish (channels close together), mid-bright, diffuse ---
        channel_spread = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        local_mean = cv2.blur(gray, (9, 9))
        local_sq_mean = cv2.blur(gray * gray, (9, 9))
        local_variance = local_sq_mean - local_mean * local_mean
        local_std = np.sqrt(np.maximum(local_variance, 0))

        color_mask = (s < 60) & (v > 90) & (v < 235) & (channel_spread < 30)
        texture_mask = (local_std > SMOKE_TEXTURE_MIN) & (local_std < SMOKE_TEXTURE_MAX)
        smoke_mask = color_mask & texture_mask
        smoke_ratio = float(smoke_mask.sum()) / total_pixels

        fire_detected = fire_ratio > FIRE_AREA_THRESHOLD
        fire_confidence = min(1.0, fire_ratio / FIRE_AREA_SATURATED) if fire_detected else round(fire_ratio / FIRE_AREA_THRESHOLD * 0.5, 3)

        smoke_detected = smoke_ratio > SMOKE_AREA_THRESHOLD
        smoke_confidence = min(1.0, smoke_ratio / SMOKE_AREA_SATURATED) if smoke_detected else round(smoke_ratio / SMOKE_AREA_THRESHOLD * 0.5, 3)

        return SmokeFireResult(
            fire_detected=fire_detected,
            fire_confidence=round(min(1.0, fire_confidence), 3),
            fire_area_ratio=round(fire_ratio, 4),
            smoke_detected=smoke_detected,
            smoke_confidence=round(min(1.0, smoke_confidence), 3),
            smoke_area_ratio=round(smoke_ratio, 4),
        )


smoke_fire_detector = SmokeFireDetector()
