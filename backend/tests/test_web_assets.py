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


def test_assets_bien_id_range_filter_excludes_out_of_range(
    client, admin_user
):

    _login_and_seed(client)

    response = client.get(
        "/assets",
        params={"bien_id_from": "1002", "bien_id_to": "1003"}
    )

    assert response.status_code == 200
    assert "2 biens trouvés" in response.text
    assert "Ecran sorti tot" in response.text
    assert "Imprimante sortie tard" in response.text
    assert "PC actif" not in response.text


def test_assets_bien_id_range_filter_is_numeric_not_lexicographic(
    client, admin_user
):
    """
    bien_id est stocké en texte : la plage doit comparer les valeurs
    numériquement (9 <= 10 <= 20), pas comme des chaînes (où "10" < "9").
    """

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
        "9;Bien numero 9;\n"
        "10;Bien numero 10;\n"
        "21;Bien numero 21;\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    response = client.get(
        "/assets",
        params={"bien_id_from": "9", "bien_id_to": "20"}
    )

    assert response.status_code == 200
    assert "2 biens trouvés" in response.text
    assert "Bien numero 9" in response.text
    assert "Bien numero 10" in response.text
    assert "Bien numero 21" not in response.text


def test_assets_no_bien_id_filter_shows_all(client, admin_user):

    _login_and_seed(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert "3 biens trouvés" in response.text
