import pytest

from app.services.glpi_service import (
    GlpiImportService,
    InvalidEncodingError,
    MissingColumnsError,
    DuplicateBienIdError,
    pad_numero_piece,
)


HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
)


def _row(inventaire, piece, lieu="Bâtiment A > Bureau 021", statut="En service"):

    return (
        f'"PC-01";"Entité";"{statut}";"Ordinateur";"Modèle";"{lieu}";'
        f'"user";"usager";"{inventaire}";"";"SN123";"";"{piece}"\n'
    )


def test_parse_extracts_bien_id_numero_piece_lieu_and_statut():

    content = (HEADER + _row("20260001", "01100021")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows == [
        ("20260001", "01100021", "Bâtiment A > Bureau 021", "En service")
    ]


def test_pad_numero_piece_completes_to_eight_characters():

    assert pad_numero_piece("600001") == "00600001"
    assert pad_numero_piece("1101043") == "01101043"
    assert pad_numero_piece("00600001") == "00600001"


def test_pad_numero_piece_leaves_empty_value_untouched():

    assert pad_numero_piece("") == ""
    assert pad_numero_piece(None) is None


def test_parse_pads_numero_piece_to_eight_characters():

    content = (HEADER + _row("20260001", "600001")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows[0][1] == "00600001"


def test_parse_leaves_empty_numero_piece_untouched():

    content = (HEADER + _row("20260001", "")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows[0][1] == ""


def test_parse_leaves_empty_lieu_and_statut_untouched():

    content = (
        HEADER + _row("20260001", "01100021", lieu="", statut="")
    ).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows == [("20260001", "01100021", "", "")]


def test_parse_skips_rows_without_bien_id():

    content = (HEADER + _row("", "01100021")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows == []


def test_parse_strips_utf8_bom():

    content = (HEADER + _row("20260001", "01100021")).encode("utf-8-sig")

    rows = GlpiImportService.parse(content)

    assert rows[0][0] == "20260001"
    assert rows[0][1] == "01100021"


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
