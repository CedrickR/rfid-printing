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


def test_job_detail_shows_print_pdf_button(client, admin_user):

    job_url = _login_and_create_job(client)

    response = client.get(job_url)

    assert response.status_code == 200
    assert "Imprimer / Exporter en PDF" in response.text
    assert "window.print()" in response.text


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
