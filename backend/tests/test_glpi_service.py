import pytest

from app.services.glpi_service import (
    GlpiImportService,
    InvalidEncodingError,
    MissingColumnsError,
    DuplicateBienIdError,
)


HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
)


def _row(inventaire, piece):

    return (
        '"PC-01";"Entité";"Statut";"Ordinateur";"Modèle";"Lieu";'
        f'"user";"usager";"{inventaire}";"";"SN123";"";"{piece}"\n'
    )


def test_parse_extracts_bien_id_and_numero_piece():

    content = (HEADER + _row("20260001", "01100021")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows == [("20260001", "01100021")]


def test_parse_skips_rows_without_bien_id():

    content = (HEADER + _row("", "01100021")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows == []


def test_parse_strips_utf8_bom():

    content = (HEADER + _row("20260001", "01100021")).encode("utf-8-sig")

    rows = GlpiImportService.parse(content)

    assert rows == [("20260001", "01100021")]


def test_parse_raises_on_missing_columns():

    content = (
        '"Nom";"Entité"\n"PC-01";"Entité1"\n'
    ).encode("utf-8")

    with pytest.raises(MissingColumnsError) as exc_info:
        GlpiImportService.parse(content)

    assert "Numéro d'inventaire" in exc_info.value.missing_columns
    assert "Numéro de la pièce" in exc_info.value.missing_columns


def test_parse_raises_on_duplicate_bien_id():

    content = (
        HEADER + _row("20260001", "01100021") + _row("20260001", "01100022")
    ).encode("utf-8")

    with pytest.raises(DuplicateBienIdError) as exc_info:
        GlpiImportService.parse(content)

    assert exc_info.value.duplicated_ids == ["20260001"]


def test_parse_raises_on_invalid_encoding():

    content = b"\xff\xfe\x00invalid"

    with pytest.raises(InvalidEncodingError):
        GlpiImportService.parse(content)
