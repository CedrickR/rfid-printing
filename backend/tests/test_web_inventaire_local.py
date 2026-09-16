import re


def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _login_manager(client):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )


def _login_reader(client):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )


def _import_asset(
    client, bien_id="10001", designation="PC Portable",
    local_libelle="SALLE 101", sortie=""
):

    csv_content = (
        "numero;libelle;sortie;local_libelle\n"
        f"{bien_id};{designation};{sortie};{local_libelle}\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def test_inventaire_local_page_requires_login(client):

    response = client.get("/inventaire-local", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_inventaire_local_page_denies_reader_role(client, standard_user):

    _login_reader(client)

    response = client.get("/inventaire-local")

    assert response.status_code == 403


def test_inventaire_local_page_accessible_to_manager_role(
    client, manager_user
):

    _login_manager(client)

    response = client.get("/inventaire-local")

    assert response.status_code == 200


def test_inventaire_local_page_without_local_shows_no_table(
    client, admin_user
):

    _login(client)

    response = client.get("/inventaire-local")

    assert response.status_code == 200
    assert "Ajouter un bien en trop" not in response.text


def test_inventaire_local_page_lists_active_assets_of_selected_local(
    client, admin_user
):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert response.status_code == 200
    assert "10001" in response.text
    assert "PC Portable" in response.text
    assert "Présent" in response.text


def test_inventaire_local_page_excludes_inactive_assets(
    client, admin_user
):

    _login(client)
    _import_asset(
        client, "10001", "PC sorti", "SALLE 101", sortie="2020-01-01"
    )

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert "Aucun bien actif affecté à ce local." in response.text


def test_inventaire_local_page_excludes_other_locals(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 202"}
    )

    assert "10001" not in response.text
    assert "Aucun bien actif affecté à ce local." in response.text


def test_inventaire_local_page_shows_type_bien_from_inventory(
    client, admin_user
):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Copieur"})
    _import_asset(client, "10001", "Copieur RDC", "SALLE 101")

    asset_id = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()[0]["id"]

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    client.post(
        f"/assets/{asset_id}/type-bien",
        data={"type_bien_id": asset_type_id}
    )

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert "Copieur" in response.text


def test_inventaire_local_lines_are_not_duplicated_on_repeat_view(
    client, admin_user
):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    client.get("/inventaire-local", params={"local": "SALLE 101"})
    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert response.text.count("10001") == 1


def test_add_extra_line_appears_with_present_status(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.post(
        "/inventaire-local/add",
        data={
            "local": "SALLE 101",
            "bien_id": "EXTRA1",
            "type_bien_id": "",
            "commentaire": "trouvé sous le bureau"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?local=SALLE%20101&added=1"
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert "EXTRA1" in page.text
    assert "En trop" in page.text
    assert "trouvé sous le bureau" in page.text


def test_add_extra_line_requires_bien_id(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "   "}
    )

    assert response.status_code == 400
    assert "obligatoires" in response.text


def test_add_extra_line_requires_manager_role(client, standard_user):

    _login_reader(client)

    response = client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    assert response.status_code == 403


def test_update_line_changes_statut_and_commentaire(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={
            "local": "SALLE 101",
            "statut": "Absent",
            "commentaire": "non trouvé lors du contrôle"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?local=SALLE%20101&updated=1"
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert "non trouvé lors du contrôle" in page.text


def test_update_line_sets_type_bien_on_known_asset(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Copieur"})
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={
            "local": "SALLE 101",
            "statut": "Présent",
            "type_bien_id": asset_type_id
        }
    )

    # Reflété sur l'Inventaire : une seule valeur partagée, pas une
    # copie propre à la ligne de suivi.
    inventaire_page = client.get("/assets")

    assert re.search(
        r'value="' + asset_type_id + r'"\s*selected', inventaire_page.text
    )

    local_page = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert re.search(
        r'value="' + asset_type_id + r'"\s*selected', local_page.text
    )


def test_update_line_sets_type_bien_on_extra_line(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Caisson"})

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={
            "local": "SALLE 101",
            "statut": "Présent",
            "type_bien_id": asset_type_id
        }
    )

    local_page = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert re.search(
        r'value="' + asset_type_id + r'"\s*selected', local_page.text
    )


def test_update_line_rejects_invalid_statut(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "Perdu"}
    )

    assert response.status_code == 400
    assert "invalide" in response.text


def test_update_missing_line_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/lines/999/update",
        data={"local": "SALLE 101", "statut": "Absent"}
    )

    assert response.status_code == 404


def test_delete_extra_line_removes_it(client, admin_user):

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/delete",
        data={"local": "SALLE 101"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?local=SALLE%20101&deleted=1"
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert "EXTRA1" not in page.text


def test_delete_known_line_is_rejected(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/delete",
        data={"local": "SALLE 101"}
    )

    assert response.status_code == 400
    assert "en trop" in response.text


def test_delete_missing_line_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/lines/999/delete",
        data={"local": "SALLE 101"}
    )

    assert response.status_code == 404


def test_export_csv_includes_known_and_extra_lines(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    client.post(
        "/inventaire-local/add",
        data={
            "local": "SALLE 101",
            "bien_id": "EXTRA1",
            "commentaire": "trouvé sur place"
        }
    )

    response = client.get(
        "/inventaire-local/export-csv", params={"local": "SALLE 101"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == "Bien ID;Désignation;Type de bien;Commentaire;Statut"
    assert "10001;PC Portable;;;Présent" in lines
    assert "EXTRA1;;;trouvé sur place;Présent" in lines
