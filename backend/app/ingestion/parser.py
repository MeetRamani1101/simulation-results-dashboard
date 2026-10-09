"""CSV parsing and validation for frequency-response result files.

A file either parses completely and cleanly, or is rejected with a specific,
actionable error. We deliberately do not do "best effort" partial parsing
(e.g. silently dropping bad rows) because a truncated or partially-corrupt
dataset could understate the true peak magnitude and misrepresent a failing
revision as passing.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

EXPECTED_HEADER_PREFIXES = ("frequency", "magnitude")


class CsvValidationError(ValueError):
    """Raised when a results CSV cannot be safely imported."""


@dataclass(frozen=True)
class ParsedCsv:
    samples: list[tuple[float, float]]  # (frequency_hz, magnitude_mm), sorted by frequency
    frequency_unit: str
    magnitude_unit: str


def _split_header_label(cell: str) -> tuple[str, str]:
    cell = cell.strip()
    if "[" in cell and cell.endswith("]"):
        name, unit = cell.split("[", 1)
        return name.strip(), unit.rstrip("]").strip()
    return cell, ""


def parse_results_csv(path: Path) -> ParsedCsv:
    if not path.exists():
        raise CsvValidationError(f"File not found: {path}")
    if path.stat().st_size == 0:
        raise CsvValidationError("File is empty")

    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvValidationError(f"File is not valid UTF-8 text: {exc}") from exc

    rows = list(csv.reader(text.splitlines()))
    rows = [r for r in rows if any(cell.strip() for cell in r)]  # drop blank lines
    if not rows:
        raise CsvValidationError("File has no data rows")

    header = rows[0]
    if len(header) != 2:
        raise CsvValidationError(
            f"Expected exactly 2 columns (Frequency, Magnitude), found {len(header)}"
        )

    freq_name, freq_unit = _split_header_label(header[0])
    mag_name, mag_unit = _split_header_label(header[1])
    header_looks_valid = freq_name.strip().lower().startswith(
        EXPECTED_HEADER_PREFIXES[0]
    ) and mag_name.strip().lower().startswith(EXPECTED_HEADER_PREFIXES[1])

    if header_looks_valid:
        data_rows = rows[1:]
    else:
        # No recognizable header - treat every row (including the first) as data,
        # but only if it actually parses as numbers; otherwise this is a genuine
        # header/format mismatch and must be rejected rather than guessed at.
        data_rows = rows
        freq_unit, mag_unit = "Hz", "mm"

    if not data_rows:
        raise CsvValidationError("File has a header row but no data rows")

    samples: list[tuple[float, float]] = []
    for line_no, row in enumerate(data_rows, start=2 if header_looks_valid else 1):
        if len(row) != 2:
            raise CsvValidationError(f"Line {line_no}: expected 2 columns, found {len(row)}")
        raw_freq, raw_mag = row[0].strip(), row[1].strip()
        try:
            freq = float(raw_freq)
            mag = float(raw_mag)
        except ValueError:
            raise CsvValidationError(
                f"Line {line_no}: non-numeric value ('{raw_freq}', '{raw_mag}')"
            ) from None
        if freq < 0:
            raise CsvValidationError(f"Line {line_no}: negative frequency ({freq})")
        if mag < 0:
            raise CsvValidationError(f"Line {line_no}: negative magnitude ({mag})")
        samples.append((freq, mag))

    samples.sort(key=lambda pair: pair[0])
    return ParsedCsv(
        samples=samples,
        frequency_unit=freq_unit or "Hz",
        magnitude_unit=mag_unit or "mm",
    )
