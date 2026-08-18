GLPI_HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
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


def _upload_inventory(client, numero="1001", libelle="PC Portable"):

    csv_content = (
        "numero;libelle;sortie\n"
        f"{numero};{libelle};\n"
    )

    return client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")},
        follow_redirects=False
    )


def _upload_rfid_scan(client):

    csv_content = "L26100000001;26120260001\n"

    return client.post(
        "/rfid-scans",
        files={"file": ("scan.csv", csv_content, "text/csv")},
        follow_redirects=False
    )


def _upload_glpi(client, bien_id="20260001", piece="01100099"):

    content = (
        GLPI_HEADER
        + f'"PC-01";"Entité";"En service";"Ordinateur";"Modèle";'
        f'"SIEGE";"user";"usager";"{bien_id}";"";"SN123";"";"{piece}"\n'
    )

    return client.post(
        "/glpi-locations",
        data={"glpi_type": "ordinateur"},
        files={"file": ("glpi.csv", content, "text/csv")},
        follow_redirects=False
    )


def test_backups_page_requires_login(client):

    response = client.get("/admin/backups", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_backups_page_requires_admin_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.get("/admin/backups")

    assert response.status_code == 403


def test_backups_page_denies_reader_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/admin/backups")

    assert response.status_code == 403


def test_backups_page_shows_no_backups_message(client, admin_user):

    _login(client)

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert "Aucune sauvegarde disponible." in response.text


def test_manual_backup_creation_appears_in_history(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/backups",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/backups?created=1"

    listing = client.get("/admin/backups?created=1")

    assert listing.status_code == 200
    assert "Sauvegarde créée." in listing.text
    assert "Sauvegarde manuelle" in listing.text
    assert "1 / 2" in listing.text


def test_manual_backup_creation_requires_admin_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.post("/admin/backups")

    assert response.status_code == 403


def test_import_inventaire_triggers_auto_backup(client, admin_user):

    _login(client)
    _upload_inventory(client)

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert "Import inventaire" in response.text
    assert "1 / 2" in response.text


def test_rfid_scan_import_triggers_auto_backup(client, admin_user):

    _login(client)
    _upload_rfid_scan(client)

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert "Import scan RFID" in response.text
    assert "1 / 2" in response.text


def test_glpi_import_triggers_auto_backup(client, admin_user):

    _login(client)
    _upload_glpi(client)

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert "Import GLPI" in response.text
    assert "1 / 2" in response.text


def test_backup_retention_keeps_only_two_most_recent(client, admin_user):

    _login(client)

    for _ in range(3):
        client.post("/admin/backups")

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert "2 / 2" in response.text


def test_restore_backup_replaces_current_data(client, admin_user):

    _login(client)

    _upload_inventory(client, numero="1001", libelle="Premier bien")

    backups_page = client.get("/admin/backups")
    filename = backups_page.text.split(
        '/admin/backups/'
    )[1].split('/restore')[0]

    _upload_inventory(client, numero="1002", libelle="Second bien")

    assets_before = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()

    assert len(assets_before) == 2

    response = client.post(
        f"/admin/backups/{filename}/restore",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/backups?restored=1"

    assets_after = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()

    assert len(assets_after) == 1
    assert assets_after[0]["bien_id"] == "1001"


def test_restore_missing_backup_returns_404(client, admin_user):

    _login(client)

    response = client.post("/admin/backups/does-not-exist.db/restore")

    assert response.status_code == 404
    assert "introuvable" in response.text


def test_restore_backup_requires_admin_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.post("/admin/backups/whatever.db/restore")

    assert response.status_code == 403


def test_delete_backup_removes_it_from_list(client, admin_user):

    _login(client)
    client.post("/admin/backups")

    backups_page = client.get("/admin/backups")
    filename = backups_page.text.split(
        '/admin/backups/'
    )[1].split('/restore')[0]

    response = client.post(
        f"/admin/backups/{filename}/delete",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/backups?deleted=1"

    listing = client.get("/admin/backups?deleted=1")

    assert listing.status_code == 200
    assert "Sauvegarde supprimée." in listing.text
    assert "Aucune sauvegarde disponible." in listing.text


def test_delete_missing_backup_returns_404(client, admin_user):

    _login(client)

    response = client.post("/admin/backups/does-not-exist.db/delete")

    assert response.status_code == 404
    assert "introuvable" in response.text


def test_backups_restore_and_delete_forms_have_confirmation(
    client, admin_user
):

    _login(client)
    client.post("/admin/backups")

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert 'onsubmit="return confirm(' in response.text
    assert response.text.count('onsubmit="return confirm(') >= 2


def test_backups_page_shows_reset_database_danger_zone(client, admin_user):

    _login(client)

    response = client.get("/admin/backups")

    assert response.status_code == 200
    assert 'action="/admin/reset-database"' in response.text
    assert "Vider la base de données" in response.text
