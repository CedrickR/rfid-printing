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


def test_users_page_requires_login(client):

    response = client.get("/admin/users", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_users_page_requires_admin_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/admin/users")

    assert response.status_code == 403


def test_users_page_denies_manager_role(client, manager_user):

    _login(client, "gestionnaire", "Gestionnaire123!")

    response = client.get("/admin/users")

    assert response.status_code == 403


def test_users_page_lists_existing_users(client, admin_user):

    _login(client)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert "admin" in response.text
    assert "administrateur" in response.text


def test_create_user(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/users",
        data={
            "username": "nouveau",
            "password": "MotDePasse1!",
            "role": "lecteur"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/users?created=1"

    listing = client.get("/admin/users")

    assert "nouveau" in listing.text

    # Le nouveau compte doit pouvoir se connecter.
    login_response = client.post(
        "/login",
        data={
            "username": "nouveau",
            "password": "MotDePasse1!",
            "next": "/dashboard"
        },
        follow_redirects=False
    )

    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/assets"


def test_create_user_rejects_duplicate_username(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/users",
        data={
            "username": "admin",
            "password": "MotDePasse1!",
            "role": "lecteur"
        }
    )

    assert response.status_code == 400


def test_create_user_rejects_invalid_role(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/users",
        data={
            "username": "nouveau",
            "password": "MotDePasse1!",
            "role": "superadmin"
        }
    )

    assert response.status_code == 400


def test_create_user_rejects_short_password(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/users",
        data={
            "username": "nouveau",
            "password": "short",
            "role": "lecteur"
        }
    )

    assert response.status_code == 400
    assert "8 caractères" in response.text


def test_update_role(client, admin_user, manager_user):

    _login(client)

    response = client.post(
        f"/admin/users/{manager_user.id}/role",
        data={"role": "lecteur"},
        follow_redirects=False
    )

    assert response.status_code == 303

    listing = client.get("/admin/users")

    assert '<span class="badge badge-secondary">lecteur</span>' in listing.text


def test_update_role_missing_user_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/users/999/role",
        data={"role": "lecteur"}
    )

    assert response.status_code == 404


def test_update_role_rejects_demoting_last_admin(client, admin_user):
    """
    L'unique administrateur ne doit pas pouvoir se rétrograder
    lui-même : cela couperait l'accès à la gestion des utilisateurs.
    """

    _login(client)

    response = client.post(
        f"/admin/users/{admin_user.id}/role",
        data={"role": "gestionnaire"}
    )

    assert response.status_code == 400
    assert "administrateur" in response.text.lower()


def test_update_role_allows_demotion_when_another_admin_remains(
    client, admin_user
):

    _login(client)

    client.post(
        "/admin/users",
        data={
            "username": "admin2",
            "password": "MotDePasse1!",
            "role": "administrateur"
        }
    )

    listing = client.get("/admin/users")

    admin2_id = None

    for row in listing.text.split("<tr>"):
        if "admin2" in row:
            # Le formulaire de rôle référence /admin/users/{id}/role
            match = re.search(r"/admin/users/(\d+)/role", row)
            if match:
                admin2_id = int(match.group(1))

    assert admin2_id is not None

    response = client.post(
        f"/admin/users/{admin2_id}/role",
        data={"role": "gestionnaire"},
        follow_redirects=False
    )

    assert response.status_code == 303


def test_reset_password(client, admin_user, manager_user):

    _login(client)

    response = client.post(
        f"/admin/users/{manager_user.id}/password",
        data={"password": "NouveauMotDePasse1!"},
        follow_redirects=False
    )

    assert response.status_code == 303

    login_response = client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "NouveauMotDePasse1!",
            "next": "/dashboard"
        },
        follow_redirects=False
    )

    assert login_response.status_code == 303
    assert "access_token" in login_response.cookies


def test_reset_password_rejects_short_password(
    client, admin_user, manager_user
):

    _login(client)

    response = client.post(
        f"/admin/users/{manager_user.id}/password",
        data={"password": "short"}
    )

    assert response.status_code == 400


def test_reset_password_missing_user_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/admin/users/999/password",
        data={"password": "MotDePasse1!"}
    )

    assert response.status_code == 404


def test_delete_user(client, admin_user, manager_user):

    _login(client)

    response = client.post(
        f"/admin/users/{manager_user.id}/delete",
        follow_redirects=False
    )

    assert response.status_code == 303

    listing = client.get("/admin/users")

    # "gestionnaire" apparaît aussi comme option de rôle dans les
    # formulaires : on vérifie la cellule d'identifiant, pas juste la
    # présence du mot dans la page.
    assert ">gestionnaire</td>" not in listing.text


def test_delete_user_rejects_self_delete(client, admin_user):

    _login(client)

    response = client.post(
        f"/admin/users/{admin_user.id}/delete"
    )

    assert response.status_code == 400
    assert "propre compte" in response.text


def test_delete_user_missing_user_returns_404(client, admin_user):

    _login(client)

    response = client.post("/admin/users/999/delete")

    assert response.status_code == 404
