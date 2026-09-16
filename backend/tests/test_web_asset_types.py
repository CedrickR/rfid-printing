def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def test_asset_types_page_requires_login(client):

    response = client.get("/admin/destinations", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_asset_types_page_requires_admin_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/admin/destinations")

    assert response.status_code == 403


def test_asset_types_page_denies_manager_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.get("/admin/destinations")

    assert response.status_code == 403


def test_asset_types_page_shows_no_asset_type_message(client, admin_user):

    _login(client)

    response = client.get("/admin/destinations")

    assert response.status_code == 200
    assert "Aucun type de bien." in response.text


def test_create_asset_type_appears_in_list(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/asset-types",
        data={"libelle": "Bureau Fauteuil"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/destinations?type_created=1"
    )

    page = client.get("/admin/destinations")

    assert "Bureau Fauteuil" in page.text


def test_create_asset_type_rejects_duplicate(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Caisson"})

    response = client.post(
        "/admin/asset-types",
        data={"libelle": "Caisson"}
    )

    assert response.status_code == 400
    assert "existe déjà" in response.text


def test_create_asset_type_rejects_empty_libelle(client, admin_user):

    _login(client)

    response = client.post("/admin/asset-types", data={"libelle": "   "})

    assert response.status_code == 400
    assert "obligatoire" in response.text


def test_create_asset_type_requires_admin_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.post(
        "/admin/asset-types",
        data={"libelle": "Armoire haute"}
    )

    assert response.status_code == 403


def test_update_asset_type_renames_it(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Armoire basse"})

    page = client.get("/admin/destinations")

    asset_type_id = page.text.split(
        '/admin/asset-types/'
    )[1].split('/update')[0]

    response = client.post(
        f"/admin/asset-types/{asset_type_id}/update",
        data={"libelle": "Armoire basse (renommée)"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/destinations?type_updated=1"
    )

    page = client.get("/admin/destinations")

    assert "Armoire basse (renommée)" in page.text
    assert "Armoire basse</td>" not in page.text


def test_update_missing_asset_type_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/asset-types/999/update",
        data={"libelle": "Copieur"}
    )

    assert response.status_code == 404
    assert "introuvable" in response.text


def test_delete_asset_type_removes_it_from_list(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Porte-Manteau"})

    page = client.get("/admin/destinations")

    asset_type_id = page.text.split(
        '/admin/asset-types/'
    )[1].split('/update')[0]

    response = client.post(
        f"/admin/asset-types/{asset_type_id}/delete",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/admin/destinations?type_deleted=1"
    )

    page = client.get("/admin/destinations")

    assert "Porte-Manteau" not in page.text


def test_delete_missing_asset_type_returns_404(client, admin_user):

    _login(client)

    response = client.post("/admin/asset-types/999/delete")

    assert response.status_code == 404
    assert "introuvable" in response.text
