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


def _row(
    inventaire,
    piece,
    lieu="Bâtiment A > Bureau 021",
    statut="En service",
    utilisateur="user",
    numero_serie="SN123"
):

    return (
        f'"PC-01";"Entité";"{statut}";"Ordinateur";"Modèle";"{lieu}";'
        f'"{utilisateur}";"usager";"{inventaire}";"";"{numero_serie}";"";'
        f'"{piece}"\n'
    )


def test_parse_extracts_bien_id_numero_piece_lieu_statut_utilisateur_and_serie():

    content = (HEADER + _row("20260001", "01100021")).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows == [
        (
            "20260001", "01100021", "Bâtiment A > Bureau 021", "En service",
            "user", "SN123"
        )
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

    assert rows == [("20260001", "01100021", "", "", "user", "SN123")]


def test_parse_leaves_empty_utilisateur_untouched():

    content = (
        HEADER + _row("20260001", "01100021", utilisateur="")
    ).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows[0][4] == ""


def test_parse_leaves_empty_numero_serie_untouched():

    content = (
        HEADER + _row("20260001", "01100021", numero_serie="")
    ).encode("utf-8")

    rows = GlpiImportService.parse(content)

    assert rows[0][5] == ""


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


def test_parse_allow_duplicates_keeps_every_occurrence():

    content = (
        HEADER
        + _row("20260001", "01100021")
        + _row("20260001", "01100022")
        + _row("20260002", "01100023")
    ).encode("utf-8")

    rows = GlpiImportService.parse_allow_duplicates(content)

    assert len(rows) == 3
    assert [row[0] for row in rows] == ["20260001", "20260001", "20260002"]


def test_parse_allow_duplicates_raises_on_missing_columns():

    content = ('"Nom";"Entité"\n"PC-01";"Entité1"\n').encode("utf-8")

    with pytest.raises(MissingColumnsError):
        GlpiImportService.parse_allow_duplicates(content)


def test_parse_allow_duplicates_raises_on_invalid_encoding():

    content = b"\xff\xfe\x00invalid"

    with pytest.raises(InvalidEncodingError):
        GlpiImportService.parse_allow_duplicates(content)


def test_find_duplicate_indices_returns_all_occurrences():

    rows = [
        ("20260001", "", "", "", "", ""),
        ("20260002", "", "", "", "", ""),
        ("20260001", "", "", "", "", ""),
        ("20260001", "", "", "", "", ""),
    ]

    assert GlpiImportService.find_duplicate_indices(rows) == {
        "20260001": [0, 2, 3]
    }


def test_find_duplicate_indices_returns_empty_dict_without_duplicates():

    rows = [
        ("20260001", "", "", "", "", ""),
        ("20260002", "", "", "", "", "")
    ]

    assert GlpiImportService.find_duplicate_indices(rows) == {}


def test_serialize_rows_round_trips_through_parse_allow_duplicates():

    rows = [
        ("20260001", "01100021", "Lieu A", "En service", "Jean", "SN1"),
        (
            "20260001", "01100022", "Lieu B;avec point-virgule",
            'Statut "cité"', "", "SN2"
        )
    ]

    content = GlpiImportService.serialize_rows(rows)

    assert GlpiImportService.parse_allow_duplicates(content) == rows
