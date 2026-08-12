


def test_import_csv(client,
    admin_user):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    csv_content = (
        "numero;"
        "libelle;"
        "sortie\n"
        "1001;PC Portable;\n"
    )

    response = client.post(
        "/api/import/",
        files={
            "file": (
                "inventaire.csv",
                csv_content,
                "text/csv"
            )
        },
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["active_assets"] == 1


def test_import_csv_comma_delimited(client, admin_user):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    csv_content = (
        "numero,"
        "libelle,"
        "sortie\n"
        "1001,PC Portable,\n"
        "1002,Ecran,2024-06-01\n"
    )

    response = client.post(
        "/api/import/",
        files={
            "file": (
                "inventaire.csv",
                csv_content,
                "text/csv"
            )
        },
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 2
    assert data["active_assets"] == 1
    assert data["excluded_assets"] == 1


def _login(client):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    return login.json()["access_token"]


def test_import_csv_skips_rows_with_missing_required_fields(
    client, admin_user
):

    token = _login(client)

    csv_content = (
        "numero;libelle;sortie\n"
        "1001;PC Portable;\n"
        ";Ecran sans id;\n"
        "1003;   ;\n"
    )

    response = client.post(
        "/api/import/",
        files={
            "file": ("inventaire.csv", csv_content, "text/csv")
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 1
    assert data["invalid_rows"] == 2


def test_import_csv_numeric_bien_id_not_corrupted_by_missing_row(
    client, admin_user
):

    token = _login(client)

    csv_content = (
        "numero;libelle;sortie\n"
        "1001;PC Portable;\n"
        ";Ligne invalide;\n"
    )

    response = client.post(
        "/api/import/",
        files={
            "file": ("inventaire.csv", csv_content, "text/csv")
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    token2 = token

    assets_response = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token2}"}
    )

    bien_ids = [a["bien_id"] for a in assets_response.json()]

    assert "1001" in bien_ids
    assert "1001.0" not in bien_ids


def test_import_csv_rejects_duplicate_bien_id(client, admin_user):

    token = _login(client)

    csv_content = (
        "numero;libelle;sortie\n"
        "1001;PC Portable;\n"
        "1001;PC Portable bis;\n"
    )

    response = client.post(
        "/api/import/",
        files={
            "file": ("inventaire.csv", csv_content, "text/csv")
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "doublon" in response.json()["detail"]


def test_import_csv_rejects_invalid_encoding(client, admin_user):

    token = _login(client)

    response = client.post(
        "/api/import/",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle\n1001;Écran".encode("latin-1"),
                "text/csv"
            )
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "Encodage" in response.json()["detail"]


def test_search_assets_is_paginated(client, admin_user):

    token = _login(client)

    csv_content = "numero;libelle;sortie\n" + "".join(
        f"{i};Ecran modele {i};\n" for i in range(1, 6)
    )

    client.post(
        "/api/import/",
        files={
            "file": ("inventaire.csv", csv_content, "text/csv")
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.get(
        "/api/import/assets/search",
        params={"q": "Ecran", "page": 1, "size": 2},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_import_csv_maps_source_columns_and_ignores_the_rest(
    client, admin_user
):
    """
    Le fichier issu du logiciel de gestion d'inventaire utilise
    numero/libelle/sortie, avec d'autres colonnes non exploitées
    (ex. categorie, emplacement) qui doivent être ignorées sans erreur.
    """

    token = _login(client)

    csv_content = (
        "numero;libelle;categorie;emplacement;sortie\n"
        "10001;PC Portable;Informatique;Bureau 12;\n"
        "10002;Imprimante;Informatique;Bureau 12;2024-06-01\n"
    )

    response = client.post(
        "/api/import/",
        files={
            "file": ("inventaire.csv", csv_content, "text/csv")
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total_rows"] == 2
    assert data["active_assets"] == 1
    assert data["excluded_assets"] == 1

    assets_response = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token}"}
    )

    assets = {a["bien_id"]: a for a in assets_response.json()}

    assert assets["10001"]["bien_designation"] == "PC Portable"
    assert assets["10001"]["is_active"] is True
    assert assets["10002"]["is_active"] is False


def test_import_csv_missing_source_column_is_reported(client, admin_user):

    token = _login(client)

    csv_content = "numero;libelle\n10001;PC Portable\n"

    response = client.post(
        "/api/import/",
        files={
            "file": ("inventaire.csv", csv_content, "text/csv")
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 400
    assert "sortie" in response.json()["detail"]