from __future__ import annotations
import math

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def quintic_smoothstep(u):
    u = clamp(float(u), 0.0, 1.0)
    return 10.0*u**3 - 15.0*u**4 + 6.0*u**5

def interpolate(q0, q1, u):
    a, b = list(q0), list(q1)
    if len(a) != len(b):
        raise ValueError("joint vector sizes differ")
    s = quintic_smoothstep(u)
    return [x + (y-x)*s for x, y in zip(a, b)]

def wrap_delta(a, b):
    return math.atan2(math.sin(a-b), math.cos(a-b))

def joint_distance_sq(a, b, weights=None):
    aa, bb = list(a), list(b)
    if weights is None:
        weights = [1.0] * len(aa)
    return sum(w * wrap_delta(x, y)**2 for x, y, w in zip(aa, bb, weights))

def posture_score(q, previous_q, reference_q):
    continuity_weights = [1.2, 1.4, 1.4, 1.0, 1.0, 1.35]
    reference_weights = [0.12, 0.12, 0.12, 0.08, 0.08, 0.10]
    score = joint_distance_sq(q, previous_q, continuity_weights)
    score += joint_distance_sq(q, reference_q, reference_weights)
    limit = 2.0 * math.pi
    for x in q:
        ratio = min(abs(x) / limit, 0.999999)
        score += 0.035 * (ratio / max(1e-6, 1.0-ratio))**2
    return score
