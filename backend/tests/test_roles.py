def _login(client, username, password):

    return client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        },
        follow_redirects=False
    )


def test_login_redirects_reader_to_assets_not_dashboard(client, standard_user):

    response = _login(client, "employe", "Employe123!")

    assert response.status_code == 303
    assert response.headers["location"] == "/assets"


def test_login_redirects_admin_to_next(client, admin_user):

    response = _login(client, "admin", "Admin123!")

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard"


def test_reader_can_access_assets_page(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/assets")

    assert response.status_code == 200


def test_reader_sees_disabled_action_buttons_on_assets_page(
    client, standard_user
):

    _login(client, "employe", "Employe123!")

    response = client.get("/assets")

    assert response.status_code == 200
    assert "Export lecteur RFID" in response.text
    assert "Inventaire immatériel" in response.text
    assert "Créer un lot d'impression" in response.text
    assert response.text.count("disabled") >= 3


def test_manager_does_not_see_disabled_action_buttons_on_assets_page(
    client, manager_user
):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.get("/assets")

    assert response.status_code == 200
    assert "disabled" not in response.text


READER_FORBIDDEN_GET_ROUTES = [
    "/dashboard",
    "/import",
    "/jobs",
    "/history",
    "/rfid-scans",
    "/settings/cmd-template",
    "/admin/users",
]


def test_reader_is_forbidden_from_all_other_pages(client, standard_user):

    _login(client, "employe", "Employe123!")

    for path in READER_FORBIDDEN_GET_ROUTES:

        response = client.get(path)

        assert response.status_code == 403, (
            f"{path} devrait être interdit au profil lecteur"
        )


def test_reader_is_forbidden_from_create_job(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.post(
        "/jobs/create",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 403


def test_reader_is_forbidden_from_export_immateriel(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.post(
        "/assets/export-immateriel",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 403


def test_reader_is_forbidden_from_export_rfid_reader(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/assets/export-rfid-reader")

    assert response.status_code == 403


def test_reader_is_forbidden_from_reset_database(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.post("/admin/reset-database")

    assert response.status_code == 403


MANAGER_ALLOWED_GET_ROUTES = [
    "/dashboard",
    "/import",
    "/assets",
    "/jobs",
    "/history",
    "/rfid-scans",
]


def test_manager_can_access_day_to_day_pages(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    for path in MANAGER_ALLOWED_GET_ROUTES:

        response = client.get(path)

        assert response.status_code == 200, (
            f"{path} devrait être accessible au profil gestionnaire"
        )


MANAGER_FORBIDDEN_GET_ROUTES = [
    "/settings/cmd-template",
    "/admin/users",
]


def test_manager_is_forbidden_from_admin_only_pages(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    for path in MANAGER_FORBIDDEN_GET_ROUTES:

        response = client.get(path)

        assert response.status_code == 403, (
            f"{path} devrait être interdit au profil gestionnaire"
        )


def test_admin_can_access_every_page(client, admin_user):

    _login(client, "admin", "Admin123!")

    for path in MANAGER_ALLOWED_GET_ROUTES + MANAGER_FORBIDDEN_GET_ROUTES:

        response = client.get(path)

        assert response.status_code == 200, (
            f"{path} devrait être accessible au profil administrateur"
        )
