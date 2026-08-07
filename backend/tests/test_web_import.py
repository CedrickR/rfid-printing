def _login(client):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )


def test_import_page_requires_login(client):

    response = client.get("/import", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_import_preview_does_not_write_to_db(client, admin_user):

    _login(client)

    csv_content = (
        "bien_id;bien_designation;bien_amort_date_sortie\n"
        "1001;PC Portable;\n"
        "1002;Ecran;2024-06-01\n"
    )

    response = client.post(
        "/import/preview",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 2
    assert data["active_assets"] == 1
    assert data["excluded_assets"] == 1
    assert "bien_id" in data["columns"]

    assets_response = client.get(
        "/api/import/assets",
        headers={
            "Authorization": f"Bearer {_get_token(client)}"
        }
    )

    assert assets_response.json() == []


def _get_token(client):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    return login.json()["access_token"]


def test_import_submit_creates_assets(client, admin_user):

    _login(client)

    csv_content = (
        "bien_id;bien_designation;bien_amort_date_sortie\n"
        "1001;PC Portable;\n"
    )

    response = client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/dashboard?imported=1")

    assets_response = client.get(
        "/api/import/assets",
        headers={
            "Authorization": f"Bearer {_get_token(client)}"
        }
    )

    assert len(assets_response.json()) == 1


def test_import_submit_shows_error_on_duplicate(client, admin_user):

    _login(client)

    csv_content = (
        "bien_id;bien_designation;bien_amort_date_sortie\n"
        "1001;PC;\n"
        "1001;PC bis;\n"
    )

    response = client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    assert response.status_code == 400
    assert "doublon" in response.text
