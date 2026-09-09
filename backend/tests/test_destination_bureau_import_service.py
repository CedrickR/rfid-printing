import pytest

from app.services.destination_bureau_import_service import (
    DestinationBureauImportService,
    InvalidEncodingError,
    MissingColumnsError,
    DuplicateBienIdError,
)


HEADER = "numero;Destination;Niveau ;Codes pièces et niveau;Nom pièces\n"


def _row(
    numero,
    destination="MAURICE FAURE",
    codes="A.00.02 GTP",
    nom_piece="Accueil",
    niveau="RdC"
):

    return f"{numero};{destination};{niveau};{codes};{nom_piece}\n"


def test_parse_extracts_bien_id_destination_and_code_piece_service():

    content = (HEADER + _row("10001")).encode("utf-8")

    rows = DestinationBureauImportService.parse(content)

    assert rows == [("10001", "MAURICE FAURE", "A.00.02 GTP")]


def test_parse_skips_rows_without_bien_id():

    content = (HEADER + _row("")).encode("utf-8")

    rows = DestinationBureauImportService.parse(content)

    assert rows == []


def test_parse_strips_utf8_bom():

    content = (HEADER + _row("10001")).encode("utf-8-sig")

    rows = DestinationBureauImportService.parse(content)

    assert rows[0][0] == "10001"


def test_parse_raises_on_missing_columns():

    content = "numero;Destination\n10001;MAURICE FAURE\n".encode("utf-8")

    with pytest.raises(MissingColumnsError) as exc_info:
        DestinationBureauImportService.parse(content)

    assert "Codes pièces et niveau" in exc_info.value.missing_columns


def test_parse_raises_on_duplicate_bien_id():

    content = (
        HEADER
        + _row("10001")
        + _row("10001", destination="VALDELIA")
    ).encode("utf-8")

    with pytest.raises(DuplicateBienIdError) as exc_info:
        DestinationBureauImportService.parse(content)

    assert exc_info.value.duplicated_ids == ["10001"]


def test_parse_raises_on_invalid_encoding():

    content = b"\xff\xfe\x00invalid"

    with pytest.raises(InvalidEncodingError):
        DestinationBureauImportService.parse(content)
