def _login_and_create_job(client):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    csv_content = (
        "numero;libelle;sortie\n"
        "1001;PC actif;\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    response = client.post(
        "/jobs/create",
        data={"asset_ids": ["1"]},
        follow_redirects=False
    )

    return response.headers["location"]


def test_job_detail_shows_export_pdf_and_csv_buttons(client, admin_user):

    job_url = _login_and_create_job(client)

    response = client.get(job_url)

    assert response.status_code == 200
    assert "Exporter en PDF" in response.text
    assert "window.print()" in response.text
    assert "Exporter en CSV" in response.text
    assert f'href="{job_url}/export-csv"' in response.text


def test_job_export_csv_contains_header_and_assets(client, admin_user):

    job_url = _login_and_create_job(client)

    response = client.get(f"{job_url}/export-csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "lot_1_" in response.headers["content-disposition"]

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == "Bien ID;Désignation"
    assert "1001;PC actif" in lines


def test_job_export_csv_requires_login(client):

    response = client.get("/jobs/1/export-csv", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_job_export_csv_missing_job_returns_404(client, admin_user):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/jobs/999/export-csv")

    assert response.status_code == 404


def test_job_export_csv_requires_manager_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/jobs/1/export-csv")

    assert response.status_code == 403


def test_job_detail_print_button_and_alerts_are_not_printed(
    client, admin_user
):
    """
    Les éléments interactifs (boutons, formulaires) et les bannières
    d'erreur ne doivent pas apparaître dans le rendu imprimé (classe
    "no-print", masquée via la feuille de style @media print).
    """

    job_url = _login_and_create_job(client)

    response = client.get(f"{job_url}?error=empty")

    assert response.status_code == 200
    assert 'class="alert alert-warning no-print"' in response.text
    assert '<div class="no-print">' in response.text
