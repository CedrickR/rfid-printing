import pytest

from app.services.rfid_scan_service import (
    RfidScanService,
    InvalidEncodingError,
    NoValidLineError,
    parse_lieu_code,
    parse_bien_code,
    format_lieu_code,
    format_bien_code,
)


def test_parse_lieu_code_extracts_numero():
    assert parse_lieu_code("L26100000001") == "00000001"


def test_parse_lieu_code_returns_none_without_prefix():
    assert parse_lieu_code("00000001") is None


def test_parse_bien_code_extracts_bien_id():
    assert parse_bien_code("26120260001") == "20260001"


def test_parse_bien_code_returns_none_without_prefix():
    assert parse_bien_code("20260001") is None


def test_format_helpers_are_inverse_of_parse():
    assert format_lieu_code("00000001") == "L26100000001"
    assert format_bien_code("20260001") == "26120260001"


def test_service_parse_valid_lines():

    content = (
        "L26100000001;26120260001\n"
        "L26100000002;26120260002\n"
    ).encode("utf-8")

    valid_lines, invalid_rows = RfidScanService.parse(content)

    assert valid_lines == [
        ("00000001", "20260001"),
        ("00000002", "20260002"),
    ]
    assert invalid_rows == 0


def test_service_parse_skips_invalid_prefix_rows():

    content = (
        "L26100000001;26120260001\n"
        "BADROW;xyz\n"
        "L26100000002;NOPREFIX\n"
    ).encode("utf-8")

    valid_lines, invalid_rows = RfidScanService.parse(content)

    assert valid_lines == [("00000001", "20260001")]
    assert invalid_rows == 2


def test_service_parse_ignores_blank_lines():

    content = (
        "L26100000001;26120260001\n"
        "\n"
        "L26100000002;26120260002\n"
    ).encode("utf-8")

    valid_lines, invalid_rows = RfidScanService.parse(content)

    assert len(valid_lines) == 2
    assert invalid_rows == 0


def test_service_parse_strips_utf8_bom():

    content = (
        "L26100000001;26120260001\n"
    ).encode("utf-8-sig")

    valid_lines, invalid_rows = RfidScanService.parse(content)

    assert valid_lines == [("00000001", "20260001")]


def test_service_parse_deduplicates_repeated_bien_id_keeping_last():

    content = (
        "L26100000001;26120260001\n"
        "L26100000099;26120260001\n"
    ).encode("utf-8")

    valid_lines, invalid_rows = RfidScanService.parse(content)

    assert valid_lines == [("00000099", "20260001")]
    assert invalid_rows == 0


def test_service_parse_raises_when_no_valid_line():

    content = "BADROW;xyz\n".encode("utf-8")

    with pytest.raises(NoValidLineError):
        RfidScanService.parse(content)


def test_service_parse_raises_on_invalid_encoding():

    content = b"\xff\xfe\x00invalid"

    with pytest.raises(InvalidEncodingError):
        RfidScanService.parse(content)


def test_export_csv_reconstructs_prefixed_columns():

    from types import SimpleNamespace

    lines = [
        SimpleNamespace(lieu_numero="00000001", bien_id="20260001"),
        SimpleNamespace(lieu_numero="00000002", bien_id="20260002"),
    ]

    csv_text = RfidScanService.export_csv(lines)

    assert csv_text == (
        "L26100000001;26120260001\n"
        "L26100000002;26120260002\n"
    )


def test_export_filename_has_timestamp_prefix():

    filename = RfidScanService.export_filename()

    assert filename.startswith("export_rfid_")
    assert filename.endswith(".csv")
