def _login_and_seed(client):

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
        "1002;Ecran sorti tot;2024-01-15\n"
        "1003;Imprimante sortie tard;2024-12-01\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def test_assets_page_requires_login(client):

    response = client.get("/assets", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_assets_date_filter_excludes_out_of_range(client, admin_user):

    _login_and_seed(client)

    response = client.get(
        "/assets",
        params={"date_from": "2024-01-01", "date_to": "2024-06-30"}
    )

    assert response.status_code == 200
    assert "1 biens trouvés" in response.text
    assert "Ecran sorti tot" in response.text
    assert "Imprimante sortie tard" not in response.text
    assert "PC actif" not in response.text


def test_assets_no_date_filter_shows_all(client, admin_user):

    _login_and_seed(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert "3 biens trouvés" in response.text
