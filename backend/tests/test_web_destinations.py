BUREAU_HEADER = "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"


def _bureau_row(
    code_piece_service,
    niveau="REZ DE CHAUSSEE",
    nom_piece="021",
    nombre_poste_prevu="2"
):

    return f"{niveau};{nom_piece};{code_piece_service};{nombre_poste_prevu}\n"


def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _upload_bureaux(client, code_piece_service="01100021", nom_piece="021"):

    content = BUREAU_HEADER + _bureau_row(
        code_piece_service, nom_piece=nom_piece
    )

    return client.post(
        "/admin/destinations/bureaux",
        files={"file": ("bureaux.csv", content, "text/csv")},
        follow_redirects=False
    )


def test_destinations_page_requires_login(client):

    response = client.get("/admin/destinations", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_destinations_page_requires_admin_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/admin/destinations")

    assert response.status_code == 403


def test_destinations_page_denies_manager_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.get("/admin/destinations")

    assert response.status_code == 403


def test_destinations_page_shows_no_destinations_message(client, admin_user):

    _login(client)

    response = client.get("/admin/destinations")

    assert response.status_code == 200
    assert "Aucune destination." in response.text


def test_create_destination_appears_in_list(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/destinations",
        data={"libelle": "Direction Informatique"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/destinations?created=1"

    listing = client.get("/admin/destinations?created=1")

    assert listing.status_code == 200
    assert "Destination créée." in listing.text
    assert "Direction Informatique" in listing.text


def test_create_destination_rejects_duplicate(client, admin_user):

    _login(client)

    client.post("/admin/destinations", data={"libelle": "Comptabilité"})

    response = client.post(
        "/admin/destinations",
        data={"libelle": "Comptabilité"}
    )

    assert response.status_code == 400
    assert "existe déjà" in response.text


def test_create_destination_rejects_empty_libelle(client, admin_user):

    _login(client)

    response = client.post("/admin/destinations", data={"libelle": "   "})

    assert response.status_code == 400
    assert "obligatoire" in response.text


def test_create_destination_requires_admin_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.post(
        "/admin/destinations",
        data={"libelle": "Comptabilité"}
    )

    assert response.status_code == 403


def test_update_destination_renames_it(client, admin_user):

    _login(client)

    client.post("/admin/destinations", data={"libelle": "Ancien nom"})

    listing = client.get("/admin/destinations")

    destination_id = listing.text.split(
        '/admin/destinations/'
    )[1].split('/update')[0]

    response = client.post(
        f"/admin/destinations/{destination_id}/update",
        data={"libelle": "Nouveau nom"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/destinations?updated=1"

    updated_listing = client.get("/admin/destinations?updated=1")

    assert "Nouveau nom" in updated_listing.text
    assert "Ancien nom" not in updated_listing.text


def test_update_missing_destination_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/destinations/999/update",
        data={"libelle": "Peu importe"}
    )

    assert response.status_code == 404
    assert "introuvable" in response.text


def test_delete_destination_removes_it_from_list(client, admin_user):

    _login(client)

    client.post("/admin/destinations", data={"libelle": "A supprimer"})

    listing = client.get("/admin/destinations")

    destination_id = listing.text.split(
        '/admin/destinations/'
    )[1].split('/update')[0]

    response = client.post(
        f"/admin/destinations/{destination_id}/delete",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/destinations?deleted=1"

    updated_listing = client.get("/admin/destinations?deleted=1")

    assert "Destination supprimée." in updated_listing.text
    assert "Aucune destination." in updated_listing.text


def test_delete_missing_destination_returns_404(client, admin_user):

    _login(client)

    response = client.post("/admin/destinations/999/delete")

    assert response.status_code == 404
    assert "introuvable" in response.text


def test_bureaux_upload_shows_last_import_info(client, admin_user):

    _login(client)

    response = _upload_bureaux(client)

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/destinations?bureaux_imported=1&added=1&updated=0"
    )

    listing = client.get(response.headers["location"])

    assert listing.status_code == 200
    assert "bureaux.csv" in listing.text
    assert ">1<" in listing.text


def test_bureaux_reimport_updates_existing_code_piece_service(
    client, admin_user
):

    _login(client)

    _upload_bureaux(client, code_piece_service="01100021", nom_piece="021")

    response = _upload_bureaux(
        client, code_piece_service="01100021", nom_piece="099"
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/destinations?bureaux_imported=1&added=0&updated=1"
    )


def test_bureaux_upload_rejects_non_csv_file(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/destinations/bureaux",
        files={"file": ("bureaux.txt", BUREAU_HEADER, "text/plain")}
    )

    assert response.status_code == 400
    assert "CSV" in response.text


def test_bureaux_upload_reports_missing_columns(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/destinations/bureaux",
        files={"file": ("bureaux.csv", "niveau;nom_piece\nREZ;021\n", "text/csv")}
    )

    assert response.status_code == 400
    assert "Colonnes manquantes" in response.text


def test_bureaux_upload_requires_admin_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = _upload_bureaux(client)

    assert response.status_code == 403


def test_bureaux_upload_triggers_auto_backup(client, admin_user):

    _login(client)

    _upload_bureaux(client)

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert "Import bureaux" in response.text
