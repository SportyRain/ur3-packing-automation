from __future__ import annotations
import math

def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def quintic_smoothstep(u):
    u = clamp(float(u), 0.0, 1.0)
    return 10.0*u**3 - 15.0*u**4 + 6.0*u**5

def wrap_delta(a, b):
    return math.atan2(math.sin(a-b), math.cos(a-b))

def unwrap_near(q, reference):
    return [r + wrap_delta(x, r) for x, r in zip(q, reference)]

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

def cubic_bezier3(p0, p1, p2, p3, u):
    u = clamp(float(u), 0.0, 1.0)
    v = 1.0-u
    return tuple(
        v**3*a + 3*v*v*u*b + 3*v*u*u*c + u**3*d
        for a,b,c,d in zip(p0,p1,p2,p3)
    )

def quat_normalize(q):
    n = math.sqrt(sum(x*x for x in q))
    if n < 1e-12:
        return (0.0,0.0,0.0,1.0)
    return tuple(x/n for x in q)

def quat_slerp(q0, q1, u):
    q0 = quat_normalize(q0)
    q1 = quat_normalize(q1)
    dot = sum(a*b for a,b in zip(q0,q1))
    if dot < 0.0:
        q1 = tuple(-x for x in q1)
        dot = -dot
    dot = clamp(dot, -1.0, 1.0)
    if dot > 0.9995:
        return quat_normalize(tuple((1-u)*a + u*b for a,b in zip(q0,q1)))
    theta0 = math.acos(dot)
    sin0 = math.sin(theta0)
    a = math.sin((1-u)*theta0)/sin0
    b = math.sin(u*theta0)/sin0
    return tuple(a*x + b*y for x,y in zip(q0,q1))

def catmull_rom(qs, u):
    if not qs:
        raise ValueError("empty path")
    if len(qs) == 1:
        return list(qs[0])
    u = clamp(float(u), 0.0, 1.0)
    if u <= 0.0:
        return list(qs[0])
    if u >= 1.0:
        return list(qs[-1])

    nseg = len(qs)-1
    x = u*nseg
    i = min(int(math.floor(x)), nseg-1)
    t = x-i
    p0 = qs[max(0,i-1)]
    p1 = qs[i]
    p2 = qs[i+1]
    p3 = qs[min(len(qs)-1,i+2)]
    out = []
    for a,b,c,d in zip(p0,p1,p2,p3):
        out.append(0.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out

def sample_polyline(qs, u):
    if not qs:
        raise ValueError("empty path")
    if len(qs) == 1:
        return list(qs[0])
    u = clamp(float(u), 0.0, 1.0)
    if u <= 0.0:
        return list(qs[0])
    if u >= 1.0:
        return list(qs[-1])
    nseg = len(qs)-1
    x = u*nseg
    i = min(int(math.floor(x)), nseg-1)
    t = x-i
    return [(1.0-t)*a+t*b for a,b in zip(qs[i], qs[i+1])]
