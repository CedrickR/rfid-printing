import pytest

from app.services.bureau_service import (
    BureauImportService,
    InvalidEncodingError,
    MissingColumnsError,
    DuplicateCodePieceServiceError,
)


HEADER = "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"


def _row(
    code_piece_service,
    niveau="REZ DE CHAUSSEE",
    nom_piece="021-ENTREPOT",
    nombre_poste_prevu="2"
):

    return f"{niveau};{nom_piece};{code_piece_service};{nombre_poste_prevu}\n"


def test_parse_extracts_niveau_nom_piece_code_and_nombre_poste_prevu():

    content = (HEADER + _row("01100021")).encode("utf-8")

    rows = BureauImportService.parse(content)

    assert rows == [
        ("REZ DE CHAUSSEE", "021-ENTREPOT", "01100021", 2)
    ]


def test_parse_skips_rows_without_code_piece_service():

    content = (HEADER + _row("")).encode("utf-8")

    rows = BureauImportService.parse(content)

    assert rows == []


def test_parse_defaults_nombre_poste_prevu_to_zero_when_blank_or_invalid():

    content = (
        HEADER
        + _row("01100021", nombre_poste_prevu="")
        + _row("01100022", nombre_poste_prevu="abc")
    ).encode("utf-8")

    rows = BureauImportService.parse(content)

    assert rows[0][3] == 0
    assert rows[1][3] == 0


def test_parse_strips_utf8_bom():

    content = (HEADER + _row("01100021")).encode("utf-8-sig")

    rows = BureauImportService.parse(content)

    assert rows[0][2] == "01100021"


def test_parse_raises_on_missing_columns():

    content = "niveau;nom_piece\nREZ;021\n".encode("utf-8")

    with pytest.raises(MissingColumnsError) as exc_info:
        BureauImportService.parse(content)

    assert "code_piece_service" in exc_info.value.missing_columns
    assert "nombre_poste_prevu" in exc_info.value.missing_columns


def test_parse_raises_on_duplicate_code_piece_service():

    content = (
        HEADER
        + _row("01100021")
        + _row("01100021", nom_piece="022-REPRO")
    ).encode("utf-8")

    with pytest.raises(DuplicateCodePieceServiceError) as exc_info:
        BureauImportService.parse(content)

    assert exc_info.value.duplicated_codes == ["01100021"]


def test_parse_raises_on_invalid_encoding():

    content = b"\xff\xfe\x00invalid"

    with pytest.raises(InvalidEncodingError):
        BureauImportService.parse(content)
