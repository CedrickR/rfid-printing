import re


GLPI_HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
)

BUREAU_HEADER = "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"


def _glpi_row(inventaire, piece="01100021"):

    return (
        f'"PC-01";"Entité";"En service";"Ordinateur";"Modèle";"SIEGE";'
        f'"user";"usager";"{inventaire}";"";"SN123";"";"{piece}"\n'
    )


def _upload_glpi(client, inventaire, glpi_type):

    content = GLPI_HEADER + _glpi_row(inventaire)

    return client.post(
        "/glpi-locations",
        data={"glpi_type": glpi_type},
        files={"file": ("glpi.csv", content, "text/csv")},
        follow_redirects=False
    )


def _upload_bureau(
    client,
    code_piece_service="01100021",
    niveau="REZ DE CHAUSSEE",
    nom_piece="021-ENTREPOT",
    nombre_poste_prevu="1"
):

    content = BUREAU_HEADER + (
        f"{niveau};{nom_piece};{code_piece_service};{nombre_poste_prevu}\n"
    )

    return client.post(
        "/admin/destinations/bureaux",
        files={"file": ("bureaux.csv", content, "text/csv")},
        follow_redirects=False
    )


def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _get_token(client):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    return login.json()["access_token"]


def _asset_ids(client):

    response = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {_get_token(client)}"}
    )

    return {a["bien_id"]: a["id"] for a in response.json()}


def _set_destination(client, asset_id, destination):

    client.post(
        f"/assets/{asset_id}/destination",
        data={"destination": destination}
    )


def test_dashboard_shows_no_data_message_when_no_active_assets(
    client, admin_user
):

    _login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert response.text.count("Aucun bien actif.") == 2
    assert 'id="destinationChart"' not in response.text
    assert 'id="labelsGeneratedChart"' not in response.text


def test_dashboard_destination_chart_reflects_assignments(
    client, admin_user
):

    _login(client)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie\n"
                "1001;PC Un;\n"
                "1002;PC Deux;\n"
                "1003;PC Trois;\n",
                "text/csv"
            )
        }
    )

    client.post("/admin/destinations", data={"libelle": "Direction Info"})
    client.post("/admin/destinations", data={"libelle": "Comptabilite"})

    ids = _asset_ids(client)

    _set_destination(client, ids["1001"], "Direction Info")
    _set_destination(client, ids["1002"], "Direction Info")
    _set_destination(client, ids["1003"], "Comptabilite")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="destinationChart"' in response.text
    assert '"Direction Info"' in response.text
    assert '"Comptabilite"' in response.text
    # 2 pour Direction Info, 1 pour Comptabilite
    assert "[2, 1]" in response.text or "[2,1]" in response.text


def test_dashboard_destination_chart_excludes_inactive_assets(
    client, admin_user
):

    _login(client)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie\n"
                "1001;PC actif;\n"
                "1002;PC sorti;2024-01-01\n",
                "text/csv"
            )
        }
    )

    client.post("/admin/destinations", data={"libelle": "Direction Info"})

    ids = _asset_ids(client)

    _set_destination(client, ids["1001"], "Direction Info")
    _set_destination(client, ids["1002"], "Direction Info")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "[1]" in response.text


def test_dashboard_shows_sans_destination_for_unassigned_assets(
    client, admin_user
):

    _login(client)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie\n1001;PC Un;\n",
                "text/csv"
            )
        }
    )

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Sans destination" in response.text


def test_dashboard_labels_generated_chart_counts_generated_jobs(
    client, admin_user
):

    _login(client)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie\n"
                "1001;PC Un;\n"
                "1002;PC Deux;\n",
                "text/csv"
            )
        }
    )

    ids = _asset_ids(client)

    job_location = client.post(
        "/jobs/create",
        data={"asset_ids": [str(ids["1001"])]},
        follow_redirects=False
    ).headers["location"]

    job_id = job_location.rstrip("/").split("/")[-1]

    client.post(f"/jobs/{job_id}/generate")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="labelsGeneratedChart"' in response.text

    match = re.search(
        r"labelsGeneratedChart.*?data:\s*\[\s*(\d+)\s*,\s*(\d+)\s*\]",
        response.text,
        re.S
    )

    assert match is not None
    assert match.group(1) == "1"
    assert match.group(2) == "1"


def test_dashboard_bureau_repartition_shows_no_bureau_message(
    client, admin_user
):

    _login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Aucun bureau importé." in response.text


def test_dashboard_bureau_repartition_counts_ordinateurs_and_ecrans(
    client, admin_user
):

    _login(client)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;PC Un;;01100021\n"
                "1002;Ecran Un;;01100021\n",
                "text/csv"
            )
        }
    )

    _upload_bureau(client, nombre_poste_prevu="1")

    _upload_glpi(client, "1001", "ordinateur")
    _upload_glpi(client, "1002", "moniteur")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "REZ DE CHAUSSEE" in response.text
    assert "021-ENTREPOT" in response.text
    assert "01100021" in response.text

    # 1 poste prévu -> 1 ordinateur attendu (réel : 1, écart nul) et
    # 2 écrans attendus (réel : 1, écart de -1 mis en évidence).
    assert "table-danger" in response.text


def test_dashboard_bureau_repartition_highlights_gap_when_no_assets(
    client, admin_user
):

    _login(client)

    _upload_bureau(client, nombre_poste_prevu="1")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "table-danger" in response.text
    assert "-1" in response.text
    assert "-2" in response.text


def test_dashboard_bureau_repartition_denies_reader_role(
    client, standard_user
):

    _login(client, "employe", "Employe123!")

    response = client.get("/dashboard")

    assert response.status_code == 403
