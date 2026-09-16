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
    assert response.text.count("Aucun bien actif.") == 3
    assert 'id="destinationChart"' not in response.text
    assert 'id="labelsGeneratedChart"' not in response.text
    assert 'id="printedByDestinationChart"' not in response.text


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


def test_dashboard_printed_by_destination_chart_counts_printed_and_not(
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

    ids = _asset_ids(client)

    _set_destination(client, ids["1001"], "Direction Info")
    _set_destination(client, ids["1002"], "Direction Info")
    _set_destination(client, ids["1003"], "Direction Info")

    job_location = client.post(
        "/jobs/create",
        data={"asset_ids": [str(ids["1001"])]},
        follow_redirects=False
    ).headers["location"]

    job_id = job_location.rstrip("/").split("/")[-1]

    client.post(f"/jobs/{job_id}/generate")

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert 'id="printedByDestinationChart"' in response.text
    assert '"Direction Info"' in response.text

    printed_match = re.search(
        r'"Imprimées"[^}]*data:\s*\(?\s*\[\s*(\d+)\s*\]', response.text, re.S
    )
    not_printed_match = re.search(
        r'"Non imprimées"[^}]*data:\s*\(?\s*\[\s*(\d+)\s*\]', response.text, re.S
    )

    assert printed_match is not None
    assert not_printed_match is not None
    assert printed_match.group(1) == "1"
    assert not_printed_match.group(1) == "2"


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


def _validated_by_local_check_count(page_text):

    match = re.search(
        r'Biens validés \(suivi par local\)\s*</div>\s*'
        r'<div class="h5 mb-0 font-weight-bold text-gray-800">\s*'
        r'(\d+)\s*</div>',
        page_text
    )

    assert match, "Compteur 'Biens validés (suivi par local)' introuvable"

    return int(match.group(1))


def test_dashboard_shows_zero_validated_by_local_check_without_activity(
    client, admin_user
):

    _login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert _validated_by_local_check_count(response.text) == 0


def test_dashboard_counts_asset_validated_via_local_check(
    client, admin_user
):

    _login(client)

    csv_content = (
        "numero;libelle;sortie;local_libelle\n"
        "10001;PC Portable;;SALLE 101\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    # Le seul affichage du local crée la ligne (statut par défaut,
    # auteur "system") mais ne doit pas encore compter comme validé.
    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    response = client.get("/dashboard")

    assert _validated_by_local_check_count(response.text) == 0

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "Présent"}
    )

    response = client.get("/dashboard")

    assert _validated_by_local_check_count(response.text) == 1


def _mobilier_repartition_row_counts(page_text, code_piece_service):
    """
    Le code pièce et service apparaît aussi sur l'onglet "Répartition
    par bureau" (autres colonnes) : on isole d'abord le contenu de
    l'onglet "Répartition du mobilier par bureau" avant de chercher la
    ligne du bureau demandé.
    """

    mobilier_section = page_text.split(
        'id="mobilier-repartition-pane"'
    )[1]

    row_html = mobilier_section.split(code_piece_service)[1].split(
        "</tr>"
    )[0]

    return re.findall(r'text-center">(\d+)</td>', row_html)


def test_dashboard_mobilier_repartition_shows_no_type_message(
    client, admin_user
):

    _login(client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Répartition du mobilier par bureau" in response.text
    assert "Aucun type de bien défini" in response.text


def test_dashboard_mobilier_repartition_counts_by_type_and_bureau(
    client, admin_user
):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Bureau Fauteuil"})
    client.post("/admin/asset-types", data={"libelle": "Caisson"})

    _upload_bureau(client, code_piece_service="01100021", nom_piece="021")

    client.post(
        "/import",
        files={
            "file": (
                "inv.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;Fauteuil 1;;01100021\n"
                "1002;Fauteuil 2;;01100021\n"
                "1003;Caisson 1;;01100021\n",
                "text/csv"
            )
        }
    )

    token = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    ).json()["access_token"]

    assets = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    asset_types_page = client.get("/admin/destinations").text

    def _asset_type_id(libelle):

        position = asset_types_page.index(libelle)

        return re.search(
            r'/admin/asset-types/(\d+)/update', asset_types_page[position:]
        ).group(1)

    fauteuil_type_id = _asset_type_id("Bureau Fauteuil")
    caisson_type_id = _asset_type_id("Caisson")

    for asset in assets:

        type_id = (
            fauteuil_type_id
            if asset["bien_id"] in ("1001", "1002")
            else caisson_type_id
        )

        client.post(
            f"/assets/{asset['id']}/type-bien",
            data={"type_bien_id": type_id}
        )

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "01100021" in response.text

    counts = _mobilier_repartition_row_counts(response.text, "01100021")

    assert counts == ["2", "1"]


def test_dashboard_mobilier_repartition_ignores_assets_without_type(
    client, admin_user
):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Bureau Fauteuil"})

    _upload_bureau(client, code_piece_service="01100021", nom_piece="021")

    client.post(
        "/import",
        files={
            "file": (
                "inv.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;Sans type;;01100021\n",
                "text/csv"
            )
        }
    )

    response = client.get("/dashboard")

    counts = _mobilier_repartition_row_counts(response.text, "01100021")

    assert counts == ["0"]


def test_dashboard_mobilier_repartition_denies_reader_role(
    client, standard_user
):

    _login(client, "employe", "Employe123!")

    response = client.get("/dashboard")

    assert response.status_code == 403


def test_dashboard_shows_renamed_informatique_tab(client, admin_user):

    _login(client)

    response = client.get("/dashboard")

    assert "Répartition de l'informatique par bureau" in response.text


def test_dashboard_tables_use_striped_rows(client, admin_user):

    _login(client)

    response = client.get("/dashboard")

    assert "table-striped" in response.text


def test_export_csv_informatique_includes_expected_columns(
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

    response = client.get("/dashboard/export-csv-informatique")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == (
        "Niveau;Nom pièce;Code pièce et service;Postes prévus;"
        "Ordinateurs attendus;Ordinateurs réels;Écart ordinateurs;"
        "Écrans attendus;Écrans réels;Écart écrans"
    )
    assert "REZ DE CHAUSSEE;021-ENTREPOT;01100021;1;1;1;0;2;1;-1" in lines


def test_export_csv_informatique_requires_manager_role(
    client, standard_user
):

    _login(client, "employe", "Employe123!")

    response = client.get("/dashboard/export-csv-informatique")

    assert response.status_code == 403


def test_export_csv_mobilier_includes_expected_columns(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Bureau Fauteuil"})
    client.post("/admin/asset-types", data={"libelle": "Caisson"})

    _upload_bureau(client, code_piece_service="01100021", nom_piece="021")

    client.post(
        "/import",
        files={
            "file": (
                "inv.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;Fauteuil 1;;01100021\n"
                "1002;Caisson 1;;01100021\n",
                "text/csv"
            )
        }
    )

    token = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    ).json()["access_token"]

    assets = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    asset_types_page = client.get("/admin/destinations").text

    def _asset_type_id(libelle):

        position = asset_types_page.index(libelle)

        return re.search(
            r'/admin/asset-types/(\d+)/update', asset_types_page[position:]
        ).group(1)

    fauteuil_type_id = _asset_type_id("Bureau Fauteuil")
    caisson_type_id = _asset_type_id("Caisson")

    for asset in assets:

        type_id = (
            fauteuil_type_id
            if asset["bien_id"] == "1001"
            else caisson_type_id
        )

        client.post(
            f"/assets/{asset['id']}/type-bien",
            data={"type_bien_id": type_id}
        )

    response = client.get("/dashboard/export-csv-mobilier")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == (
        "Niveau;Nom pièce;Code pièce et service;Bureau Fauteuil;Caisson"
    )
    assert "REZ DE CHAUSSEE;021;01100021;1;1" in lines


def test_export_csv_mobilier_requires_manager_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.get("/dashboard/export-csv-mobilier")

    assert response.status_code == 403
