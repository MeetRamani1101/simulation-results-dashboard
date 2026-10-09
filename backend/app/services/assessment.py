"""Pure, side-effect-free functions implementing the engineering review rule.

Kept isolated from the database/ingestion/API layers so the assessment logic
can be unit tested directly and reused anywhere (ingestion cache, on-the-fly
comparison, etc.) without pulling in SQLAlchemy or FastAPI.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import ASSESSMENT_FREQ_MAX_HZ, ASSESSMENT_FREQ_MIN_HZ, ASSESSMENT_LIMIT_MM


@dataclass(frozen=True)
class Assessment:
    limit_mm: float
    freq_min_hz: float
    freq_max_hz: float
    assessed_max_magnitude: float | None
    assessed_peak_frequency: float | None
    overall_max_magnitude: float | None
    overall_max_frequency: float | None
    passes_limit: bool | None
    sample_count: int

    @property
    def metric_name(self) -> str:
        return f"max_magnitude_{int(self.freq_min_hz)}_{int(self.freq_max_hz)}hz"


def assess_samples(
    samples: list[tuple[float, float]],
    *,
    limit_mm: float = ASSESSMENT_LIMIT_MM,
    freq_min_hz: float = ASSESSMENT_FREQ_MIN_HZ,
    freq_max_hz: float = ASSESSMENT_FREQ_MAX_HZ,
) -> Assessment:
    """Compute the pass/fail assessment and peak values for one revision.

    ``samples`` is a list of ``(frequency_hz, magnitude_mm)`` pairs. The pass
    criterion only looks at samples with ``freq_min_hz <= frequency <= freq_max_hz``
    (inclusive on both ends, per the stated review rule); samples above that
    range are still reported via the overall peak for visualization purposes.
    """
    in_range = [(f, m) for f, m in samples if freq_min_hz <= f <= freq_max_hz]

    assessed_max_magnitude = None
    assessed_peak_frequency = None
    passes_limit = None
    if in_range:
        assessed_peak_frequency, assessed_max_magnitude = max(in_range, key=lambda pair: pair[1])
        passes_limit = assessed_max_magnitude <= limit_mm

    overall_max_magnitude = None
    overall_max_frequency = None
    if samples:
        overall_max_frequency, overall_max_magnitude = max(samples, key=lambda pair: pair[1])

    return Assessment(
        limit_mm=limit_mm,
        freq_min_hz=freq_min_hz,
        freq_max_hz=freq_max_hz,
        assessed_max_magnitude=assessed_max_magnitude,
        assessed_peak_frequency=assessed_peak_frequency,
        overall_max_magnitude=overall_max_magnitude,
        overall_max_frequency=overall_max_frequency,
        passes_limit=passes_limit,
        sample_count=len(samples),
    )
