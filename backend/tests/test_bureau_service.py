import pytest

from app.services.bureau_service import (
    BureauImportService,
    InvalidEncodingError,
    MissingColumnsError,
    DuplicateCodelieuError,
)


HEADER = "codelieu;batiment;etage;bureau\n"


def _row(codelieu, batiment="SIEGE", etage="REZ DE CHAUSSEE", bureau="021"):

    return f"{codelieu};{batiment};{etage};{bureau}\n"


def test_parse_extracts_codelieu_batiment_etage_bureau():

    content = (HEADER + _row("01100021")).encode("utf-8")

    rows = BureauImportService.parse(content)

    assert rows == [
        ("01100021", "SIEGE", "REZ DE CHAUSSEE", "021")
    ]


def test_parse_skips_rows_without_codelieu():

    content = (HEADER + _row("")).encode("utf-8")

    rows = BureauImportService.parse(content)

    assert rows == []


def test_parse_strips_utf8_bom():

    content = (HEADER + _row("01100021")).encode("utf-8-sig")

    rows = BureauImportService.parse(content)

    assert rows[0][0] == "01100021"


def test_parse_raises_on_missing_columns():

    content = "codelieu;batiment\n01100021;SIEGE\n".encode("utf-8")

    with pytest.raises(MissingColumnsError) as exc_info:
        BureauImportService.parse(content)

    assert "etage" in exc_info.value.missing_columns
    assert "bureau" in exc_info.value.missing_columns


def test_parse_raises_on_duplicate_codelieu():

    content = (
        HEADER + _row("01100021") + _row("01100021", bureau="022")
    ).encode("utf-8")

    with pytest.raises(DuplicateCodelieuError) as exc_info:
        BureauImportService.parse(content)

    assert exc_info.value.duplicated_codes == ["01100021"]


def test_parse_raises_on_invalid_encoding():

    content = b"\xff\xfe\x00invalid"

    with pytest.raises(InvalidEncodingError):
        BureauImportService.parse(content)
