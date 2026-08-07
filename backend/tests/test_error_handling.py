def _login(client):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )


def test_api_error_stays_json(client, admin_user):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    response = client.get(
        "/api/print/jobs/999",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Lot introuvable"}


def test_web_error_renders_html_page(client, admin_user):

    _login(client)

    response = client.get("/jobs/999")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "404" in response.text
    assert "Lot introuvable" in response.text
    # rendu via base.html, pas un JSON brut
    assert "RFID Printing" in response.text
