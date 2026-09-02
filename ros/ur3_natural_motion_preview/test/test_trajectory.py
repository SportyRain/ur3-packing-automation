import math
import pytest
from ur3_natural_motion_preview.trajectory import (
    quintic_smoothstep, interpolate, wrap_delta, posture_score
)

def test_minimum_jerk_endpoints():
    assert quintic_smoothstep(0.0) == pytest.approx(0.0)
    assert quintic_smoothstep(1.0) == pytest.approx(1.0)
    assert quintic_smoothstep(0.5) == pytest.approx(0.5)

def test_interpolation():
    assert interpolate([0]*6, [1]*6, 0.5) == pytest.approx([0.5]*6)

def test_wrap_delta():
    assert abs(wrap_delta(math.pi-0.1, -math.pi+0.1)) == pytest.approx(0.2)

def test_score_prefers_continuity():
    prev = [0.0]*6
    ref = [0.0]*6
    assert posture_score([0.1]*6, prev, ref) < posture_score([2.0]*6, prev, ref)
