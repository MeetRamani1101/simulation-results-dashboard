import pytest

from app.ingestion.parser import CsvValidationError, parse_results_csv
from tests.conftest import write_csv


def test_parses_valid_csv(tmp_path):
    p = tmp_path / "Bracket.csv"
    write_csv(p, [(5.0, 2.1), (21.3, 2.9), (32.2, 6.3)])
    result = parse_results_csv(p)
    assert result.samples == [(5.0, 2.1), (21.3, 2.9), (32.2, 6.3)]
    assert result.frequency_unit == "Hz"
    assert result.magnitude_unit == "mm"


def test_sorts_out_of_order_rows(tmp_path):
    p = tmp_path / "x.csv"
    write_csv(p, [(30.0, 1.0), (5.0, 2.0)])
    result = parse_results_csv(p)
    assert [f for f, _ in result.samples] == [5.0, 30.0]


def test_missing_file_raises(tmp_path):
    with pytest.raises(CsvValidationError):
        parse_results_csv(tmp_path / "missing.csv")


def test_empty_file_raises(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(CsvValidationError):
        parse_results_csv(p)


def test_header_only_raises(tmp_path):
    p = tmp_path / "header_only.csv"
    p.write_text("Frequency [Hz],Magnitude [mm]\n", encoding="utf-8")
    with pytest.raises(CsvValidationError, match="no data rows"):
        parse_results_csv(p)


def test_non_numeric_row_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("Frequency [Hz],Magnitude [mm]\n5.0,oops\n", encoding="utf-8")
    with pytest.raises(CsvValidationError, match="non-numeric"):
        parse_results_csv(p)


def test_wrong_column_count_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("Frequency [Hz],Magnitude [mm],Extra\n5.0,1.0,2.0\n", encoding="utf-8")
    with pytest.raises(CsvValidationError, match="2 columns"):
        parse_results_csv(p)


def test_negative_values_raise(tmp_path):
    p = tmp_path / "bad.csv"
    write_csv(p, [(-1.0, 1.0)])
    with pytest.raises(CsvValidationError, match="negative"):
        parse_results_csv(p)


def test_headerless_numeric_data_is_accepted(tmp_path):
    p = tmp_path / "no_header.csv"
    p.write_text("5.0,2.1\n10.0,3.4\n", encoding="utf-8")
    result = parse_results_csv(p)
    assert result.samples == [(5.0, 2.1), (10.0, 3.4)]


def test_ragged_row_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("Frequency [Hz],Magnitude [mm]\n5.0,1.0\n10.0\n", encoding="utf-8")
    with pytest.raises(CsvValidationError, match="Line 3"):
        parse_results_csv(p)
