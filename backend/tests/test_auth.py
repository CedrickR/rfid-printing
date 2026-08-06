

def test_login(
    client,
    admin_user
):

    response = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    assert response.status_code == 200


def test_me(client,
    admin_user):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200