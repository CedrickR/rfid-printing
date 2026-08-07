


def test_get_assets(client, admin_user):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/api/import/assets",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200