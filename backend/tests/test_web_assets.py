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


def _login_and_seed_many(client, count):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    rows = "\n".join(
        f"{i};Bien numero {i};" for i in range(1, count + 1)
    )

    csv_content = "numero;libelle;sortie\n" + rows + "\n"

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def test_assets_default_page_size_is_ten(client, admin_user):

    _login_and_seed_many(client, 30)

    response = client.get("/assets")

    assert response.status_code == 200
    assert response.text.count("Bien numero ") == 10


def test_assets_page_size_25(client, admin_user):

    _login_and_seed_many(client, 30)

    response = client.get("/assets", params={"page_size": "25"})

    assert response.status_code == 200
    assert response.text.count("Bien numero ") == 25


def test_assets_page_size_50(client, admin_user):

    _login_and_seed_many(client, 30)

    response = client.get("/assets", params={"page_size": "50"})

    assert response.status_code == 200
    assert response.text.count("Bien numero ") == 30


def test_assets_invalid_page_size_falls_back_to_ten(client, admin_user):

    _login_and_seed_many(client, 30)

    response = client.get("/assets", params={"page_size": "999"})

    assert response.status_code == 200
    assert response.text.count("Bien numero ") == 10


def _login_and_seed_locations(client):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    csv_content = (
        "numero;libelle;sortie;local_numero;immeuble_libelle;"
        "niveau_libelle;local_libelle\n"
        "10001;PC Portable;;01100021;SIEGE;REZ DE CHAUSSEE;021-ENTREPOT\n"
        "10002;Ecran;;01100023;SIEGE;REZ DE CHAUSSEE;023-REPRO\n"
        "10003;Imprimante;;02200001;ANNEXE;1ER ETAGE;101-BUREAU\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def test_assets_immeuble_filter(client, admin_user):

    _login_and_seed_locations(client)

    response = client.get("/assets", params={"immeuble": "SIEGE"})

    assert response.status_code == 200
    assert "2 biens trouvés" in response.text
    assert "PC Portable" in response.text
    assert "Ecran" in response.text
    assert "Imprimante" not in response.text


def test_assets_niveau_and_local_filter_combine(client, admin_user):

    _login_and_seed_locations(client)

    response = client.get(
        "/assets",
        params={"niveau": "REZ DE CHAUSSEE", "local": "023-REPRO"}
    )

    assert response.status_code == 200
    assert "1 biens trouvés" in response.text
    assert "Ecran" in response.text
    assert "PC Portable" not in response.text


def test_assets_page_lists_filter_options_from_existing_data(
    client, admin_user
):

    _login_and_seed_locations(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert "SIEGE" in response.text
    assert "ANNEXE" in response.text
    assert "1ER ETAGE" in response.text


def test_export_immateriel_requires_selection(client, admin_user):

    _login_and_seed_locations(client)

    response = client.post(
        "/assets/export-immateriel",
        data={},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets?error=no_selection"


def test_export_immateriel_generates_csv_from_selected_assets(
    client, admin_user
):

    _login_and_seed_locations(client)

    response = client.post(
        "/assets/export-immateriel",
        data={"asset_ids": ["1", "2"]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "inventaire_immateriel_" in response.headers["content-disposition"]
    assert "L26101100021;26110001" in response.text
    assert "L26101100023;26110002" in response.text


def test_export_immateriel_skips_assets_without_local_numero(
    client, admin_user
):

    _login_and_seed(client)

    response = client.post(
        "/assets/export-immateriel",
        data={"asset_ids": ["1"]},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets?error=no_location"


def test_export_rfid_reader_requires_login(client):

    response = client.get("/assets/export-rfid-reader", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_export_rfid_reader_contains_only_active_assets(client, admin_user):

    _login_and_seed(client)

    response = client.get("/assets/export-rfid-reader")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "lecteur_rfid_" in response.headers["content-disposition"]
    assert response.text == "1001;PC actif\n"


def test_export_rfid_reader_is_semicolon_separated_bien_id_and_designation(
    client, admin_user
):

    _login_and_seed_locations(client)

    response = client.get("/assets/export-rfid-reader")

    assert response.status_code == 200
    assert "10001;PC Portable\n" in response.text
    assert "10002;Ecran\n" in response.text
    assert "10003;Imprimante\n" in response.text


def test_export_rfid_reader_empty_when_no_active_assets(client, admin_user):

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
        "1001;PC sorti;2024-01-15\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )

    response = client.get("/assets/export-rfid-reader")

    assert response.status_code == 200
    assert response.text == ""


def test_export_csv_requires_login(client):

    response = client.get("/assets/export-csv", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_export_csv_contains_header_and_all_matching_rows(
    client, admin_user
):

    _login_and_seed(client)

    response = client.get("/assets/export-csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "inventaire_" in response.headers["content-disposition"]

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == (
        "Bien ID;Désignation;Numéro local;Immeuble;Niveau;Local;"
        "Destination;Bureau;Utilisateur;Actif"
    )
    assert len(lines) == 4  # en-tête + 3 biens
    assert "1001;PC actif;;;;;;;;Actif" in lines
    assert "1002;Ecran sorti tot;;;;;;;;Exclu" in lines


def test_export_csv_respects_search_filters(client, admin_user):

    _login_and_seed(client)

    response = client.get(
        "/assets/export-csv",
        params={"bien_id_from": "1002", "bien_id_to": "1003"}
    )

    assert response.status_code == 200

    lines = response.text.strip("\n").split("\n")

    assert len(lines) == 3  # en-tête + 2 biens
    assert "PC actif" not in response.text
    assert "Ecran sorti tot" in response.text
    assert "Imprimante sortie tard" in response.text


def test_export_csv_is_not_limited_by_page_size(client, admin_user):

    _login_and_seed_many(client, 30)

    response = client.get("/assets/export-csv")

    assert response.status_code == 200
    assert response.text.count("Bien numero ") == 30


def test_export_csv_accessible_to_reader_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/assets/export-csv")

    assert response.status_code == 200


def test_export_csv_includes_destination_and_bureau(client, admin_user):

    _login_and_seed(client)

    client.post(
        "/import",
        files={
            "file": (
                "loc.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;PC actif;;01100021\n",
                "text/csv"
            )
        }
    )

    client.post("/admin/destinations", data={"libelle": "Direction Info"})

    client.post(
        "/admin/destinations/bureaux",
        files={
            "file": (
                "bureaux.csv",
                "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"
                "REZ DE CHAUSSEE;021-A;01100021;2\n",
                "text/csv"
            )
        }
    )

    asset_id = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()[0]["id"]

    client.post(
        f"/assets/{asset_id}/destination",
        data={"destination": "Direction Info"}
    )

    response = client.get("/assets/export-csv")

    assert response.status_code == 200

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == (
        "Bien ID;Désignation;Numéro local;Immeuble;Niveau;Local;"
        "Destination;Bureau;Utilisateur;Actif"
    )
    assert (
        "1001;PC actif;01100021;;;;Direction Info;"
        "REZ DE CHAUSSEE - 021-A;;Actif" in lines
    )


def test_assets_page_shows_bureau_as_concatenated_fields(client, admin_user):

    _login_and_seed(client)

    client.post(
        "/import",
        files={
            "file": (
                "loc.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;PC actif;;01100021\n",
                "text/csv"
            )
        }
    )

    client.post(
        "/admin/destinations/bureaux",
        files={
            "file": (
                "bureaux.csv",
                "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"
                "REZ DE CHAUSSEE;021-A;01100021;2\n",
                "text/csv"
            )
        }
    )

    response = client.get("/assets")

    assert response.status_code == 200
    assert "REZ DE CHAUSSEE - 021-A" in response.text


def test_assets_page_shows_no_last_import_when_database_empty(
    client, admin_user
):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/assets")

    assert response.status_code == 200
    assert "Dernière importation" not in response.text


def test_assets_page_shows_last_import_date_and_user(client, admin_user):

    _login_and_seed(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert "Dernière importation" in response.text
    assert "par admin" in response.text


def test_assets_page_shows_most_recent_import_when_several(
    client, admin_user
):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    client.post(
        "/import",
        files={
            "file": (
                "premier.csv",
                "numero;libelle;sortie\n1001;Bien 1;\n",
                "text/csv"
            )
        }
    )

    client.post(
        "/import",
        files={
            "file": (
                "second.csv",
                "numero;libelle;sortie\n1002;Bien 2;\n",
                "text/csv"
            )
        }
    )

    response = client.get("/assets")

    assert response.status_code == 200
    assert response.text.count("Dernière importation") == 1


def test_assets_page_shows_destination_and_bureau_columns(client, admin_user):

    _login_and_seed(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert "Destination" in response.text
    assert "Bureau" in response.text


def test_assets_page_shows_bureau_from_mapping(client, admin_user):

    _login_and_seed(client)

    client.post(
        "/import",
        files={
            "file": (
                "loc.csv",
                "numero;libelle;sortie;local_numero\n"
                "1001;PC actif;;01100021\n",
                "text/csv"
            )
        }
    )

    client.post(
        "/admin/destinations/bureaux",
        files={
            "file": (
                "bureaux.csv",
                "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"
                "REZ DE CHAUSSEE;021-A;01100021;2\n",
                "text/csv"
            )
        }
    )

    response = client.get("/assets")

    assert response.status_code == 200
    assert "021-A" in response.text


def test_update_asset_destination_sets_value(client, admin_user):

    _login_and_seed(client)

    client.post("/admin/destinations", data={"libelle": "Direction Info"})

    asset_id = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()[0]["id"]

    response = client.post(
        f"/assets/{asset_id}/destination",
        data={"destination": "Direction Info", "next": "/assets"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets"

    listing = client.get("/assets")

    assert 'selected' in listing.text
    assert "Direction Info" in listing.text


def test_update_asset_destination_requires_manager_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/assets/1/destination",
        data={"destination": "Direction Info"}
    )

    assert response.status_code == 403


def test_update_asset_destination_missing_asset_returns_404(
    client, admin_user
):

    _login_and_seed(client)

    response = client.post(
        "/assets/999/destination",
        data={"destination": "Direction Info"}
    )

    assert response.status_code == 404


def test_update_asset_destination_ignores_unsafe_next(client, admin_user):

    _login_and_seed(client)

    asset_id = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()[0]["id"]

    response = client.post(
        f"/assets/{asset_id}/destination",
        data={"destination": "Direction Info", "next": "https://evil.example"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets"


def _upload_bureau(client, code_piece_service="01100021", nom_piece="021-A"):

    client.post(
        "/admin/destinations/bureaux",
        files={
            "file": (
                "bureaux.csv",
                "niveau;nom_piece;code_piece_service;nombre_poste_prevu\n"
                f"REZ DE CHAUSSEE;{nom_piece};{code_piece_service};2\n",
                "text/csv"
            )
        }
    )


def test_assets_page_shows_bureau_dropdown_with_code_piece_service(
    client, admin_user
):

    _login_and_seed(client)
    _upload_bureau(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert 'name="code_piece_service"' in response.text
    assert 'value="01100021"' in response.text
    assert "021-A" in response.text
    assert "2 poste(s)" in response.text


def test_assets_page_shows_bureau_read_only_for_reader_role(
    client, standard_user
):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/assets")

    assert response.status_code == 200
    assert 'name="code_piece_service"' not in response.text


def test_update_asset_bureau_sets_local_numero(client, admin_user):

    _login_and_seed(client)
    _upload_bureau(client)

    asset_id = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()[0]["id"]

    response = client.post(
        f"/assets/{asset_id}/bureau",
        data={"code_piece_service": "01100021", "next": "/assets"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets"

    listing = client.get("/assets")

    assert 'selected' in listing.text
    assert "021-A" in listing.text


def test_update_asset_bureau_requires_manager_role(client, standard_user):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )

    response = client.post(
        "/assets/1/bureau",
        data={"code_piece_service": "01100021"}
    )

    assert response.status_code == 403


def test_update_asset_bureau_missing_asset_returns_404(client, admin_user):

    _login_and_seed(client)

    response = client.post(
        "/assets/999/bureau",
        data={"code_piece_service": "01100021"}
    )

    assert response.status_code == 404


def test_update_asset_bureau_ignores_unsafe_next(client, admin_user):

    _login_and_seed(client)
    _upload_bureau(client)

    asset_id = client.get(
        "/api/import/assets",
        headers={
            "Authorization": "Bearer "
            + client.post(
                "/auth/login",
                json={"username": "admin", "password": "Admin123!"}
            ).json()["access_token"]
        }
    ).json()[0]["id"]

    response = client.post(
        f"/assets/{asset_id}/bureau",
        data={
            "code_piece_service": "01100021",
            "next": "https://evil.example"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets"


GLPI_HEADER = (
    '"Nom";"Entité";"Statut";"Type";"Modèle";"Lieu";"Utilisateur";'
    '"Usager";"Numéro d\'inventaire";'
    '"Informations financières et administratives - Numéro '
    'd\'immobilisation";"Numéro de série";"Informations financières et '
    'administratives - Fournisseur";"Numéro de la pièce"\n'
)


def _upload_glpi(client, bien_id, utilisateur, glpi_type="ordinateur"):

    content = (
        GLPI_HEADER
        + f'"PC-01";"Entité";"En service";"Ordinateur";"Modèle";"SIEGE";'
        f'"{utilisateur}";"usager";"{bien_id}";"";"SN123";"";"01100021"\n'
    )

    return client.post(
        "/glpi-locations",
        data={"glpi_type": glpi_type},
        files={"file": ("glpi.csv", content, "text/csv")}
    )


def test_assets_page_shows_utilisateur_from_glpi_import(client, admin_user):

    _login_and_seed(client)
    _upload_glpi(client, "1001", "Jean Dupont")

    response = client.get("/assets")

    assert response.status_code == 200
    assert "Utilisateur" in response.text
    assert "Jean Dupont" in response.text


def test_assets_page_shows_empty_utilisateur_without_glpi_match(
    client, admin_user
):

    _login_and_seed(client)

    response = client.get("/assets")

    assert response.status_code == 200
    assert "Utilisateur" in response.text


def test_export_csv_includes_utilisateur(client, admin_user):

    _login_and_seed(client)
    _upload_glpi(client, "1001", "Jean Dupont")

    response = client.get("/assets/export-csv")

    assert response.status_code == 200

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == (
        "Bien ID;Désignation;Numéro local;Immeuble;Niveau;Local;"
        "Destination;Bureau;Utilisateur;Actif"
    )
    assert "1001;PC actif;;;;;;;Jean Dupont;Actif" in lines
