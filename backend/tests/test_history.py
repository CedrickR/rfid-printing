def test_get_history(
    client,
    admin_user
):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/api/history",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200

def test_my_history(
    client,
    admin_user
):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/api/history/me",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200
