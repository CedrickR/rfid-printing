def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def test_cmd_template_page_requires_login(client):

    response = client.get(
        "/settings/cmd-template",
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_cmd_template_page_requires_manager_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/settings/cmd-template")

    assert response.status_code == 403


def test_cmd_template_page_shows_default_template(client, admin_user):

    _login(client)

    response = client.get("/settings/cmd-template")

    assert response.status_code == 200
    assert "{{BienId}}" in response.text
    assert "{{JobId}}" in response.text
    assert "{{Immeuble}}" in response.text


def test_cmd_template_update_and_reload(client, admin_user):

    _login(client)

    response = client.post(
        "/settings/cmd-template",
        data={
            "header_template": "### LOT {{JobId}} ###\n",
            "line_template": "ETIQUETTE;{{BienId}};{{Designation}}"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/settings/cmd-template?saved=1"

    reload_response = client.get("/settings/cmd-template")

    assert "ETIQUETTE;{{BienId}};{{Designation}}" in reload_response.text


def test_cmd_template_update_rejects_empty_line_template(
    client, admin_user
):

    _login(client)

    response = client.post(
        "/settings/cmd-template",
        data={
            "header_template": "REM {{JobId}}",
            "line_template": "   "
        }
    )

    assert response.status_code == 400
    assert "vide" in response.text


def test_cmd_template_preview_uses_sample_asset_on_empty_database(
    client, admin_user
):

    _login(client)

    response = client.post(
        "/settings/cmd-template/preview",
        data={
            "header_template": "JOB {{JobId}}\n",
            "line_template": "{{BienId}}|{{Designation}}|{{Immeuble}}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["header"] == "JOB 42\n"
    assert "EXEMPLE001" in data["line"]


def test_cmd_template_preview_uses_real_asset_when_available(
    client, admin_user
):

    _login(client)

    csv_content = (
        "numero;libelle;sortie;immeuble_libelle\n"
        "10001;PC Portable;;SIEGE\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    response = client.post(
        "/settings/cmd-template/preview",
        data={
            "header_template": "JOB {{JobId}}\n",
            "line_template": "{{BienId}}|{{Designation}}|{{Immeuble}}"
        }
    )

    assert response.status_code == 200

    line = response.json()["line"]

    assert "10001|PC Portable|SIEGE" == line


def test_cmd_template_preview_leaves_unknown_placeholder_untouched(
    client, admin_user
):

    _login(client)

    response = client.post(
        "/settings/cmd-template/preview",
        data={
            "header_template": "JOB {{JobId}}\n",
            "line_template": "{{BienId}}|{{ChampInexistant}}"
        }
    )

    assert response.status_code == 200
    assert "{{ChampInexistant}}" in response.json()["line"]


def test_custom_template_is_used_when_generating_a_print_job(
    client, admin_user
):
    """
    Test d'intégration : un gabarit personnalisé enregistré est bien
    utilisé lors de la génération réelle d'un fichier .cmd, via le
    flux complet API (comme le ferait un vrai lot d'impression).
    """

    token = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    ).json()["access_token"]

    _login(client)

    client.post(
        "/settings/cmd-template",
        data={
            "header_template": "### LOT {{JobId}} ###\n",
            "line_template": (
                "ETIQUETTE;{{BienId}};{{Designation}};{{Immeuble}}"
            )
        }
    )

    csv_content = (
        "numero;libelle;sortie;immeuble_libelle\n"
        "10001;PC Portable;;SIEGE\n"
    )

    client.post(
        "/api/import/",
        files={"file": ("inventaire.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"}
    )

    assets = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    job_response = client.post(
        "/api/print/jobs",
        json={"asset_ids": [assets[0]["id"]]},
        headers={"Authorization": f"Bearer {token}"}
    )

    job_id = job_response.json()["job_id"]

    generate_response = client.post(
        f"/api/print/jobs/{job_id}/generate",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert generate_response.status_code == 200

    file_response = client.get(
        f"/api/print/jobs/{job_id}/file",
        headers={"Authorization": f"Bearer {token}"}
    )

    content = file_response.text

    assert f"### LOT {job_id} ###" in content
    assert "ETIQUETTE;10001;PC Portable;SIEGE" in content
