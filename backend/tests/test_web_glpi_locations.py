GLPI_HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
)


def _glpi_row(inventaire, piece):

    return (
        '"PC-01";"Entité";"Statut";"Ordinateur";"Modèle";"Lieu";'
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


def test_glpi_locations_page_requires_manager_role(client, standard_user):

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


def test_glpi_locations_page_accessible_to_manager(client, manager_user):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/glpi-locations")

    assert response.status_code == 200


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


def test_upload_rejects_duplicate_bien_id_in_file(client, admin_user):

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

    assert response.status_code == 400
    assert "doublon" in response.text.lower()


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


def test_glpi_locations_requires_manager_role_for_upload(client, standard_user):

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


def test_glpi_locations_requires_manager_role_for_export(client, standard_user):

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
