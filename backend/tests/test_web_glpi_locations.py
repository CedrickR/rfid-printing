GLPI_HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
)


def _glpi_row(inventaire, piece, lieu="SIEGE > 021-ENTREPOT", statut="En service"):

    return (
        f'"PC-01";"Entité";"{statut}";"Ordinateur";"Modèle";"{lieu}";'
        f'"user";"usager";"{inventaire}";"";"SN123";"";"{piece}"\n'
    )


def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _seed_inventory(client):

    csv_content = (
        "numero;libelle;sortie;local_numero;immeuble_libelle;"
        "niveau_libelle;local_libelle\n"
        "20260001;PC Portable;;01100021;SIEGE;REZ DE CHAUSSEE;021-ENTREPOT\n"
        "20260002;Ecran;;01100023;SIEGE;REZ DE CHAUSSEE;023-REPRO\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def _upload_glpi(client, inventaire, piece, glpi_type="ordinateur"):

    content = GLPI_HEADER + _glpi_row(inventaire, piece)

    return client.post(
        "/glpi-locations",
        data={"glpi_type": glpi_type},
        files={"file": ("glpi.csv", content, "text/csv")},
        follow_redirects=False
    )


def test_glpi_locations_page_requires_login(client):

    response = client.get("/glpi-locations", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_glpi_locations_page_requires_admin_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/glpi-locations")

    assert response.status_code == 403


def test_glpi_locations_page_denies_manager_role(client, manager_user):
    """
    Réservé aux administrateurs : un gestionnaire d'inventaire ne doit
    plus pouvoir accéder à la mise à jour des codes lieux.
    """

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/glpi-locations")

    assert response.status_code == 403


def test_upload_adds_new_bien_id(client, admin_user):

    _login(client)

    response = _upload_glpi(client, "20260001", "01100099")

    assert response.status_code == 303
    assert "imported=1" in response.headers["location"]
    assert "added=1" in response.headers["location"]
    assert "updated=0" in response.headers["location"]


def test_upload_updates_existing_bien_id_no_duplicate(client, admin_user):

    _login(client)

    _upload_glpi(client, "20260001", "01100099")
    response = _upload_glpi(client, "20260001", "01100050")

    assert response.status_code == 303
    assert "added=0" in response.headers["location"]
    assert "updated=1" in response.headers["location"]


def test_upload_rejects_missing_columns(client, admin_user):

    _login(client)

    response = client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={
            "file": (
                "glpi.csv",
                '"Nom";"Entité"\n"PC-01";"E1"\n',
                "text/csv"
            )
        }
    )

    assert response.status_code == 400
    assert "Colonnes manquantes" in response.text


def test_upload_shows_duplicates_table_for_duplicate_bien_id(client, admin_user):

    _login(client)

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099")
        + _glpi_row("20260001", "01100050")
    )

    response = client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )

    assert response.status_code == 200
    assert "doublon" in response.text.lower()
    assert response.text.count("corrected_bien_id_") == 2
    assert "01100099" in response.text
    assert "01100050" in response.text
    assert 'name="content_b64"' in response.text
    assert 'name="glpi_type" value="ordinateur"' in response.text


def _extract_content_b64(html):

    import re

    match = re.search(r'name="content_b64" value="([^"]*)"', html)

    assert match is not None

    return match.group(1)


def test_confirm_duplicates_finalizes_import_with_corrected_bien_ids(
    client, admin_user
):

    _login(client)

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099")
        + _glpi_row("20260001", "01100050")
    )

    upload_response = client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )

    content_b64 = _extract_content_b64(upload_response.text)

    response = client.post(
        "/glpi-locations/confirm-duplicates",
        data={
            "content_b64": content_b64,
            "glpi_type": "ordinateur",
            "filename": "glpi.csv",
            "corrected_bien_id_0": "20260001",
            "corrected_bien_id_1": "20260002"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert "imported=1" in response.headers["location"]
    assert "added=2" in response.headers["location"]
    assert "updated=0" in response.headers["location"]


def test_confirm_duplicates_still_duplicate_reshows_table(client, admin_user):

    _login(client)

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099")
        + _glpi_row("20260001", "01100050")
    )

    upload_response = client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )

    content_b64 = _extract_content_b64(upload_response.text)

    response = client.post(
        "/glpi-locations/confirm-duplicates",
        data={
            "content_b64": content_b64,
            "glpi_type": "ordinateur",
            "filename": "glpi.csv",
            "corrected_bien_id_0": "20260001",
            "corrected_bien_id_1": "20260001"
        }
    )

    assert response.status_code == 400
    assert "doublon" in response.text.lower()
    assert response.text.count("corrected_bien_id_") == 2


def test_confirm_duplicates_drops_row_with_blank_corrected_bien_id(
    client, admin_user
):

    _login(client)

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099")
        + _glpi_row("20260001", "01100050")
    )

    upload_response = client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )

    content_b64 = _extract_content_b64(upload_response.text)

    response = client.post(
        "/glpi-locations/confirm-duplicates",
        data={
            "content_b64": content_b64,
            "glpi_type": "ordinateur",
            "filename": "glpi.csv",
            "corrected_bien_id_0": "20260001",
            "corrected_bien_id_1": "   "
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert "imported=1" in response.headers["location"]
    assert "added=1" in response.headers["location"]


def test_confirm_duplicates_requires_admin_role(client, manager_user):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/glpi-locations/confirm-duplicates",
        data={
            "content_b64": "",
            "glpi_type": "ordinateur",
            "filename": "glpi.csv"
        }
    )

    assert response.status_code == 403


def test_upload_rejects_invalid_glpi_type(client, admin_user):

    _login(client)

    response = _upload_glpi(client, "20260001", "01100099", glpi_type="autre")

    assert response.status_code == 400
    assert "Type GLPI invalide" in response.text


def test_upload_rejects_non_csv_file(client, admin_user):

    _login(client)

    response = client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.txt", "content", "text/plain")}
    )

    assert response.status_code == 400
    assert "CSV" in response.text


def test_discrepancy_shown_when_numero_differs(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "20260001" in response.text
    assert "01100021" in response.text
    assert "01100099" in response.text


def test_discrepancy_shows_lieu_and_statut_columns_from_glpi(
    client, admin_user
):

    _login(client)
    _seed_inventory(client)

    content = GLPI_HEADER + _glpi_row(
        "20260001",
        "01100099",
        lieu="Bâtiment A - Bureau 021",
        statut="En panne"
    )

    client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "Bâtiment A - Bureau 021" in response.text
    assert "En panne" in response.text


def test_discrepancy_shows_actif_badge(client, admin_user):

    _login(client)

    csv_content = (
        "numero;libelle;sortie;local_numero\n"
        "20260001;PC Actif;;01100021\n"
        "20260002;PC Exclu;2024-01-01;01100023\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099")
        + _glpi_row("20260002", "01100098")
    )

    client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert '<span class="badge badge-success">' in response.text
    assert '<span class="badge badge-danger">' in response.text


def _seed_active_and_excluded_discrepancies(client):

    csv_content = (
        "numero;libelle;sortie;local_numero\n"
        "20260001;PC Actif;;01100021\n"
        "20260002;PC Exclu;2024-01-01;01100023\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099")
        + _glpi_row("20260002", "01100098")
    )

    client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )


def test_actif_column_header_shows_filter_buttons(client, admin_user):

    _login(client)
    _seed_active_and_excluded_discrepancies(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert 'href="/glpi-locations?active_filter=actif"' in response.text
    assert 'href="/glpi-locations?active_filter=exclu"' in response.text


def test_actif_filter_shows_only_active_assets(client, admin_user):

    _login(client)
    _seed_active_and_excluded_discrepancies(client)

    response = client.get(
        "/glpi-locations", params={"active_filter": "actif"}
    )

    assert response.status_code == 200
    assert "20260001" in response.text
    assert "20260002" not in response.text
    assert '<span class="badge badge-danger">' not in response.text


def test_exclu_filter_shows_only_excluded_assets(client, admin_user):

    _login(client)
    _seed_active_and_excluded_discrepancies(client)

    response = client.get(
        "/glpi-locations", params={"active_filter": "exclu"}
    )

    assert response.status_code == 200
    assert "20260002" in response.text
    assert "20260001" not in response.text
    assert '<span class="badge badge-success">' not in response.text


def test_without_filter_shows_both_active_and_excluded_assets(
    client, admin_user
):

    _login(client)
    _seed_active_and_excluded_discrepancies(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "20260001" in response.text
    assert "20260002" in response.text


def test_discrepancy_tooltip_shows_local_libelle(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert 'data-toggle="tooltip"' in response.text
    assert 'title="021-ENTREPOT"' in response.text


def test_discrepancy_no_tooltip_when_no_local_libelle(client, admin_user):

    _login(client)

    csv_content = (
        "numero;libelle;sortie;local_numero\n"
        "20260001;PC sans libellé;;01100021\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    _upload_glpi(client, "20260001", "01100099")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    # Le JS d'initialisation des infobulles (sélecteur jQuery) est
    # toujours présent en bas de page ; seule l'absence du <span>
    # d'infobulle sur la ligne du tableau est significative ici.
    assert "cursor: help" not in response.text


def test_upload_pads_numero_piece_to_eight_characters(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "600001")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "<td>00600001</td>" in response.text
    assert "<td>600001</td>" not in response.text


def test_local_choice_dropdown_shows_numero_and_designation(
    client, admin_user
):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "01100021 - 021-ENTREPOT" in response.text
    assert "01100023 - 023-REPRO" in response.text


def test_no_discrepancy_when_numero_matches(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100021")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "Aucun écart détecté" in response.text


def test_no_discrepancy_when_bien_id_unknown_to_inventory(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "99999999", "01100099")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "Aucun écart détecté" in response.text


def test_export_csv_requires_selection(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/export-csv",
        data={},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/glpi-locations?error=no_selection"


def test_export_csv_uses_current_local_numero_by_default(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/export-csv",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "codes_lieux_" in response.headers["content-disposition"]
    assert response.text == "Bien ID;Numéro local\n20260001;01100021\n"


def test_export_csv_uses_corrected_choice_when_provided(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/export-csv",
        data={
            "asset_ids": ["1"],
            "local_choice_1": "01100023"
        }
    )

    assert response.status_code == 200
    assert "20260001;01100023" in response.text


def test_export_csv_complet_uses_current_location_by_default(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/export-csv-complet",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "codes_lieux_complet_" in response.headers["content-disposition"]
    assert response.text == (
        "Bien ID;Numéro local;Immeuble;Niveau;Local\n"
        "20260001;01100021;SIEGE;REZ DE CHAUSSEE;021-ENTREPOT\n"
    )


def test_export_csv_complet_uses_location_of_corrected_numero(
    client, admin_user
):
    """
    Les colonnes de lieu doivent correspondre au numéro local corrigé
    (celui choisi dans la liste déroulante), pas au lieu actuel
    (potentiellement obsolète) du bien.
    """

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/export-csv-complet",
        data={
            "asset_ids": ["1"],
            "local_choice_1": "01100023"
        }
    )

    assert response.status_code == 200
    assert response.text == (
        "Bien ID;Numéro local;Immeuble;Niveau;Local\n"
        "20260001;01100023;SIEGE;REZ DE CHAUSSEE;023-REPRO\n"
    )


def test_export_csv_complet_requires_selection(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/export-csv-complet",
        data={},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/glpi-locations?error=no_selection"


def test_export_csv_complet_requires_admin_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/glpi-locations/export-csv-complet",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 403


def test_export_csv_complet_denies_manager_role(client, manager_user):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/glpi-locations/export-csv-complet",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 403


def test_glpi_locations_page_has_second_export_button(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "/glpi-locations/export-csv-complet" in response.text
    assert "avec colonnes de lieu" in response.text


def test_glpi_locations_requires_admin_role_for_upload(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = _upload_glpi(client, "20260001", "01100099")

    assert response.status_code == 403


def test_glpi_locations_denies_manager_role_for_upload(client, manager_user):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = _upload_glpi(client, "20260001", "01100099")

    assert response.status_code == 403


def test_glpi_locations_requires_admin_role_for_export(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/glpi-locations/export-csv",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 403


def test_glpi_locations_denies_manager_role_for_export(client, manager_user):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/glpi-locations/export-csv",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 403


def test_glpi_locations_reset_requires_login(client):

    response = client.post("/glpi-locations/reset", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_glpi_locations_reset_requires_admin_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.post("/glpi-locations/reset")

    assert response.status_code == 403


def test_glpi_locations_reset_denies_manager_role(client, manager_user):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = client.post("/glpi-locations/reset")

    assert response.status_code == 403


def test_glpi_locations_reset_clears_glpi_data(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    response = client.post(
        "/glpi-locations/reset",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/glpi-locations?reset=1"

    listing = client.get("/glpi-locations?reset=1")

    assert listing.status_code == 200
    assert "Données GLPI réinitialisées" in listing.text
    assert "Aucun import" in listing.text
    assert "Aucun écart détecté" in listing.text


def test_glpi_locations_reset_does_not_affect_inventory(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099")

    client.post("/glpi-locations/reset")

    assets = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    )

    assert len(assets.json()) == 2


def _seed_discrepancies_with_distinct_glpi_fields(client):

    csv_content = (
        "numero;libelle;sortie;local_numero\n"
        "20260001;PC Un;;01100021\n"
        "20260002;PC Deux;;01100023\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    content = (
        GLPI_HEADER
        + _glpi_row("20260001", "01100099", statut="Z-Statut")
        + _glpi_row("20260002", "01100050", statut="A-Statut")
    )

    client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")}
    )


def test_numero_piece_filter_hides_non_matching_rows(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get(
        "/glpi-locations", params={"numero_piece": "01100050"}
    )

    assert response.status_code == 200
    assert "20260002" in response.text
    assert "20260001" not in response.text


def test_statut_filter_hides_non_matching_rows(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get(
        "/glpi-locations", params={"statut": "A-Statut"}
    )

    assert response.status_code == 200
    assert "20260002" in response.text
    assert "20260001" not in response.text


def test_filters_are_repopulated_and_reset_link_shown(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get(
        "/glpi-locations", params={"numero_piece": "01100050"}
    )

    assert response.status_code == 200
    assert 'value="01100050"' in response.text
    assert "Réinitialiser les filtres" in response.text


def test_sort_by_numero_piece_orders_rows_ascending(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get(
        "/glpi-locations", params={"sort": "numero_piece"}
    )

    assert response.status_code == 200
    assert response.text.index("20260002") < response.text.index("20260001")


def test_sort_by_statut_orders_rows_ascending(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get(
        "/glpi-locations", params={"sort": "statut"}
    )

    assert response.status_code == 200
    assert response.text.index("20260002") < response.text.index("20260001")


def test_default_sort_is_by_bien_id_ascending(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert response.text.index("20260001") < response.text.index("20260002")


def test_glpi_locations_page_shows_selected_count(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert 'id="glpi-selected-count"' in response.text


def _seed_many_discrepancies(client, count):

    inventory_lines = ["numero;libelle;sortie;local_numero"]
    glpi_content = GLPI_HEADER

    for i in range(1, count + 1):

        bien_id = f"2026{i:04d}"
        local_numero = str(i).zfill(8)
        numero_piece = str(i + 900000).zfill(8)

        inventory_lines.append(
            f"{bien_id};PC {i};;{local_numero}"
        )
        glpi_content += _glpi_row(bien_id, numero_piece)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "\n".join(inventory_lines) + "\n",
                "text/csv"
            )
        }
    )

    client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", glpi_content, "text/csv")}
    )


def test_glpi_locations_page_shows_pagination_and_page_size_controls(
    client, admin_user
):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert 'id="glpi-page-size"' in response.text
    assert "Page 1 / 1" in response.text
    assert 'value="/glpi-locations?page_size=100"' in response.text
    assert 'value="/glpi-locations?page_size=250"' in response.text


def test_glpi_locations_pagination_splits_rows_across_pages(
    client, admin_user
):

    _login(client)
    _seed_many_discrepancies(client, 51)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "Page 1 / 2" in response.text
    assert "20260001" in response.text
    assert "20260050" in response.text
    assert "20260051" not in response.text
    assert 'href="/glpi-locations?page=2"' in response.text

    page_two = client.get("/glpi-locations", params={"page": 2})

    assert page_two.status_code == 200
    assert "Page 2 / 2" in page_two.text
    assert "20260051" in page_two.text
    assert "20260001" not in page_two.text
    assert 'href="/glpi-locations"' in page_two.text


def test_glpi_locations_page_size_100_shows_all_on_one_page(
    client, admin_user
):

    _login(client)
    _seed_many_discrepancies(client, 51)

    response = client.get("/glpi-locations", params={"page_size": 100})

    assert response.status_code == 200
    assert "Page 1 / 1" in response.text
    assert "20260001" in response.text
    assert "20260051" in response.text


def test_glpi_locations_invalid_page_size_falls_back_to_default(
    client, admin_user
):

    _login(client)
    _seed_many_discrepancies(client, 51)

    response = client.get("/glpi-locations", params={"page_size": 999})

    assert response.status_code == 200
    assert "Page 1 / 2" in response.text


def test_glpi_locations_out_of_range_page_is_clamped(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get("/glpi-locations", params={"page": 99})

    assert response.status_code == 200
    assert "Page 1 / 1" in response.text
    assert "sélectionné" in response.text


def test_glpi_locations_page_local_choice_has_auto_select_class(
    client, admin_user
):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_fields(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "glpi-local-choice" in response.text


def test_discrepancy_table_shows_type_glpi_column(client, admin_user):

    _login(client)
    _seed_inventory(client)
    _upload_glpi(client, "20260001", "01100099", glpi_type="ordinateur")

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert "Type (GLPI)" in response.text
    assert "Ordinateurs" in response.text


def test_type_filter_dropdown_lists_five_glpi_types(client, admin_user):

    _login(client)

    response = client.get("/glpi-locations")

    assert response.status_code == 200
    assert 'id="type_filter"' in response.text

    for label in (
        "Ordinateurs", "Moniteurs", "Périphériques", "Logiciels",
        "Imprimantes"
    ):
        assert label in response.text


def _seed_discrepancies_with_distinct_glpi_types(client):

    csv_content = (
        "numero;libelle;sortie;local_numero\n"
        "20260001;PC Un;;01100021\n"
        "20260002;Logiciel Un;;01100023\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    _upload_glpi(client, "20260001", "01100099", glpi_type="ordinateur")
    _upload_glpi(client, "20260002", "01100098", glpi_type="logiciel")


def test_type_filter_shows_only_matching_type(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_types(client)

    response = client.get("/glpi-locations", params={"type": "logiciel"})

    assert response.status_code == 200
    assert "20260002" in response.text
    assert "20260001" not in response.text


def test_invalid_type_filter_is_ignored(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_types(client)

    response = client.get("/glpi-locations", params={"type": "bogus"})

    assert response.status_code == 200
    assert "20260001" in response.text
    assert "20260002" in response.text


def test_type_filter_combined_with_reset_filters_link(client, admin_user):

    _login(client)
    _seed_discrepancies_with_distinct_glpi_types(client)

    response = client.get("/glpi-locations", params={"type": "logiciel"})

    assert response.status_code == 200
    assert "Réinitialiser les filtres" in response.text
    assert 'href="/glpi-locations"' in response.text
