def _login_web(client, username, password):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _seed_assets(client):

    csv_content = (
        "numero;libelle;sortie\n"
        "10001;PC Portable;\n"
        "10002;Ecran;2024-06-01\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def test_reset_database_requires_manager_role(client, standard_user):

    _login_web(client, "employe", "Employe123!")

    response = client.post(
        "/admin/reset-database",
        follow_redirects=False
    )

    assert response.status_code == 403


def test_reset_database_requires_login(client):

    response = client.post(
        "/admin/reset-database",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_reset_database_wipes_business_data_but_keeps_users(
    client, admin_user
):

    _login_web(client, "admin", "Admin123!")
    _seed_assets(client)

    assets_before = client.get(
        "/api/import/assets",
        headers={
            "Authorization": f"Bearer {_get_token(client)}"
        }
    )

    assert len(assets_before.json()) == 2

    response = client.post(
        "/admin/reset-database",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard?reset=1"

    token = _get_token(client)

    assets_after = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert assets_after.json() == []

    jobs_after = client.get(
        "/api/print/jobs",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert jobs_after.json() == []

    history_after = client.get(
        "/api/history",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert history_after.json() == []

    # Les comptes utilisateurs doivent survivre à la réinitialisation :
    # se reconnecter doit toujours fonctionner.
    login_after = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    assert login_after.status_code == 200


def _get_token(client):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    return login.json()["access_token"]
