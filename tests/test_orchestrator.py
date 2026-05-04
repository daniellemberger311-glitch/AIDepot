from backend.scoring.orchestrator import _assign_zone


class TestAssignZone:
    def test_zone_1_at_threshold(self):
        assert _assign_zone(76.0) == 1

    def test_zone_1_above_threshold(self):
        assert _assign_zone(95.0) == 1

    def test_zone_1_perfect_score(self):
        assert _assign_zone(100.0) == 1

    def test_zone_2_at_lower_threshold(self):
        assert _assign_zone(61.0) == 2

    def test_zone_2_upper_boundary(self):
        assert _assign_zone(75.9) == 2

    def test_zone_2_just_below_zone_1(self):
        assert _assign_zone(75.0) == 2

    def test_zone_3_at_lower_threshold(self):
        assert _assign_zone(41.0) == 3

    def test_zone_3_upper_boundary(self):
        assert _assign_zone(60.9) == 3

    def test_zone_3_just_below_zone_2(self):
        assert _assign_zone(60.0) == 3

    def test_zone_4_just_below_zone_3(self):
        assert _assign_zone(40.9) == 4

    def test_zone_4_at_zero(self):
        assert _assign_zone(0.0) == 4

    def test_boundary_76_is_zone_1(self):
        assert _assign_zone(76.0) == 1

    def test_boundary_75_is_zone_2(self):
        assert _assign_zone(75.0) == 2

    def test_boundary_61_is_zone_2(self):
        assert _assign_zone(61.0) == 2

    def test_boundary_60_is_zone_3(self):
        assert _assign_zone(60.0) == 3

    def test_boundary_41_is_zone_3(self):
        assert _assign_zone(41.0) == 3

    def test_boundary_40_is_zone_4(self):
        assert _assign_zone(40.0) == 4
