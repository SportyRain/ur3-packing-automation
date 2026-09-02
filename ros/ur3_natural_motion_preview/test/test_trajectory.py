import math
import pytest
from ur3_natural_motion_preview.trajectory import (
    quintic_smoothstep, cubic_bezier3, quat_slerp,
    catmull_rom, sample_polyline, wrap_delta, posture_score
)

def test_minimum_jerk_endpoints():
    assert quintic_smoothstep(0.0) == pytest.approx(0.0)
    assert quintic_smoothstep(1.0) == pytest.approx(1.0)

def test_bezier_endpoints():
    p0=(0.0,0.0,0.0); p1=(0.0,0.0,1.0)
    p2=(1.0,0.0,1.0); p3=(1.0,0.0,0.0)
    assert cubic_bezier3(p0,p1,p2,p3,0.0) == pytest.approx(p0)
    assert cubic_bezier3(p0,p1,p2,p3,1.0) == pytest.approx(p3)

def test_slerp_endpoints():
    q0=(0.0,0.0,0.0,1.0); q1=(0.0,0.0,1.0,0.0)
    assert quat_slerp(q0,q1,0.0) == pytest.approx(q0)
    got=quat_slerp(q0,q1,1.0)
    assert abs(got[2]) == pytest.approx(1.0)

def test_path_endpoints():
    qs=[[0.0]*6,[1.0]*6,[2.0]*6]
    assert catmull_rom(qs,0.0) == pytest.approx(qs[0])
    assert catmull_rom(qs,1.0) == pytest.approx(qs[-1])
    assert sample_polyline(qs,0.0) == pytest.approx(qs[0])
    assert sample_polyline(qs,1.0) == pytest.approx(qs[-1])

def test_wrap_delta():
    assert abs(wrap_delta(math.pi-0.1, -math.pi+0.1)) == pytest.approx(0.2)

def test_score_prefers_continuity():
    prev=[0.0]*6; ref=[0.0]*6
    assert posture_score([0.1]*6,prev,ref) < posture_score([2.0]*6,prev,ref)
