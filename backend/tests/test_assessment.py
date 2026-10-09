from app.services.assessment import assess_samples


def test_pass_when_max_in_range_at_limit():
    samples = [(10, 5.0), (30, 15.0), (60, 50.0)]  # 60Hz sample must be ignored
    result = assess_samples(samples)
    assert result.assessed_max_magnitude == 15.0
    assert result.assessed_peak_frequency == 30
    assert result.passes_limit is True


def test_fail_when_max_in_range_above_limit():
    samples = [(10, 5.0), (37.6, 19.9), (48, 1.6)]
    result = assess_samples(samples)
    assert result.assessed_max_magnitude == 19.9
    assert result.passes_limit is False


def test_boundary_frequency_50hz_is_included():
    samples = [(50.0, 20.0), (51.0, 100.0)]
    result = assess_samples(samples)
    assert result.assessed_max_magnitude == 20.0
    assert result.assessed_peak_frequency == 50.0
    assert result.passes_limit is False
    # overall peak still reflects the >50Hz sample
    assert result.overall_max_magnitude == 100.0
    assert result.overall_max_frequency == 51.0


def test_boundary_frequency_0hz_is_included():
    samples = [(0.0, 16.0), (10.0, 1.0)]
    result = assess_samples(samples)
    assert result.assessed_max_magnitude == 16.0
    assert result.passes_limit is False


def test_no_samples_in_assessment_range_yields_none_result():
    samples = [(60.0, 1.0), (80.0, 2.0)]
    result = assess_samples(samples)
    assert result.assessed_max_magnitude is None
    assert result.assessed_peak_frequency is None
    assert result.passes_limit is None
    assert result.overall_max_magnitude == 2.0


def test_empty_samples():
    result = assess_samples([])
    assert result.passes_limit is None
    assert result.overall_max_magnitude is None
    assert result.sample_count == 0


def test_exactly_at_limit_passes():
    samples = [(20.0, 15.0)]
    result = assess_samples(samples)
    assert result.passes_limit is True


def test_just_above_limit_fails():
    samples = [(20.0, 15.0001)]
    result = assess_samples(samples)
    assert result.passes_limit is False
