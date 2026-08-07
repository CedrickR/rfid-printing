def test_dashboard_redirects_to_login_when_not_authenticated(client):

    response = client.get(
        "/dashboard",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_login_page_renders(client):

    response = client.get("/login")

    assert response.status_code == 200
    assert "Se connecter" in response.text


def test_login_wrong_password_shows_error(client, admin_user):

    response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "wrong-password",
            "next": "/dashboard"
        }
    )

    assert response.status_code == 401
    assert "invalide" in response.text


def test_login_sets_cookie_and_grants_access(client, admin_user):

    login_response = client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        },
        follow_redirects=False
    )

    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/dashboard"
    assert "access_token" in login_response.cookies

    dashboard_response = client.get("/dashboard")

    assert dashboard_response.status_code == 200
    assert "Tableau de bord" in dashboard_response.text


def test_logout_clears_cookie(client, admin_user):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    client.get("/logout", follow_redirects=False)

    response = client.get(
        "/dashboard",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_generate_job_requires_manager_role(client, standard_user):

    login_response = client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        },
        follow_redirects=False
    )

    assert login_response.status_code == 303

    response = client.post(
        "/jobs/1/generate",
        follow_redirects=False
    )

    assert response.status_code == 403
