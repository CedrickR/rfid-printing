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


def test_job_detail_shows_generated_files_after_generation(
    client, admin_user
):

    job_url = _login_and_create_job(client)

    client.post(f"{job_url}/generate")

    response = client.get(job_url)

    assert response.status_code == 200
    assert "1 fichier(s) .cmd généré(s)" in response.text
    assert "generated/" in response.text
    assert "print_job_" in response.text
    assert "1001.cmd" in response.text


def test_job_detail_generate_has_no_confirmation_for_small_job(
    client, admin_user
):
    """
    Un lot de taille normale (10 étiquettes ou moins) ne doit pas
    déclencher de confirmation supplémentaire à la génération.
    """

    job_url = _login_and_create_job(client)

    response = client.get(job_url)

    assert response.status_code == 200
    assert "onsubmit=" not in response.text


def test_job_detail_generate_has_confirmation_for_large_job(
    client, admin_user
):
    """
    Cas réel remonté par un utilisateur : une sélection plus
    importante que prévue (ex. une sélection précédente restée en
    mémoire côté navigateur, §2.4) peut mener à générer bien plus
    d'étiquettes que voulu. Une confirmation est exigée au-delà de 10
    étiquettes pour permettre de s'en rendre compte avant de lancer la
    génération.
    """

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    rows = "".join(
        f"{i};Bien numero {i};\n" for i in range(1, 12)
    )

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie\n" + rows,
                "text/csv"
            )
        }
    )

    response = client.post(
        "/jobs/create",
        data={"asset_ids": [str(i) for i in range(1, 12)]},
        follow_redirects=False
    )

    job_url = response.headers["location"]

    detail_response = client.get(job_url)

    assert detail_response.status_code == 200
    assert "11 étiquettes à générer" in detail_response.text
    assert "onsubmit=\"return confirm(" in detail_response.text


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
