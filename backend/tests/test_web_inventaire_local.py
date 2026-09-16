import re


def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _login_manager(client):

    client.post(
        "/login",
        data={
            "username": "gestionnaire",
            "password": "Gestionnaire123!",
            "next": "/dashboard"
        }
    )


def _login_reader(client):

    client.post(
        "/login",
        data={
            "username": "employe",
            "password": "Employe123!",
            "next": "/dashboard"
        }
    )


def _import_asset(
    client, bien_id="10001", designation="PC Portable",
    local_libelle="SALLE 101", sortie=""
):

    csv_content = (
        "numero;libelle;sortie;local_libelle\n"
        f"{bien_id};{designation};{sortie};{local_libelle}\n"
    )

    client.post(
        "/import",
        files={"file": ("inventaire.csv", csv_content, "text/csv")}
    )


def test_inventaire_local_page_requires_login(client):

    response = client.get("/inventaire-local", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_inventaire_local_page_denies_reader_role(client, standard_user):

    _login_reader(client)

    response = client.get("/inventaire-local")

    assert response.status_code == 403


def test_inventaire_local_page_accessible_to_manager_role(
    client, manager_user
):

    _login_manager(client)

    response = client.get("/inventaire-local")

    assert response.status_code == 200


def test_inventaire_local_page_without_local_shows_no_table(
    client, admin_user
):

    _login(client)

    response = client.get("/inventaire-local")

    assert response.status_code == 200
    assert "Ajouter un bien en trop" not in response.text


def test_inventaire_local_page_lists_active_assets_of_selected_local(
    client, admin_user
):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert response.status_code == 200
    assert "10001" in response.text
    assert "PC Portable" in response.text
    assert "Présent" in response.text


def test_inventaire_local_page_excludes_inactive_assets(
    client, admin_user
):

    _login(client)
    _import_asset(
        client, "10001", "PC sorti", "SALLE 101", sortie="2020-01-01"
    )

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert "Aucun bien actif affecté à ce local." in response.text


def test_inventaire_local_page_excludes_other_locals(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 202"}
    )

    assert "10001" not in response.text
    assert "Aucun bien actif affecté à ce local." in response.text


def test_inventaire_local_page_shows_type_bien_from_inventory(
    client, admin_user
):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Copieur"})
    _import_asset(client, "10001", "Copieur RDC", "SALLE 101")

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

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    client.post(
        f"/assets/{asset_id}/type-bien",
        data={"type_bien_id": asset_type_id}
    )

    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert "Copieur" in response.text


def test_inventaire_local_lines_are_not_duplicated_on_repeat_view(
    client, admin_user
):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    client.get("/inventaire-local", params={"local": "SALLE 101"})
    response = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert response.text.count("10001") == 1


def test_add_extra_line_appears_with_present_status(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.post(
        "/inventaire-local/add",
        data={
            "local": "SALLE 101",
            "bien_id": "EXTRA1",
            "type_bien_id": "",
            "commentaire": "trouvé sous le bureau"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?local=SALLE%20101&added=1"
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert "EXTRA1" in page.text
    assert "En trop" in page.text
    assert "trouvé sous le bureau" in page.text


def test_add_extra_line_requires_bien_id(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "   "}
    )

    assert response.status_code == 400
    assert "obligatoires" in response.text


def test_add_extra_line_requires_manager_role(client, standard_user):

    _login_reader(client)

    response = client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    assert response.status_code == 403


def test_bien_id_has_no_color_before_validation(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert 'class="text-success"' not in response.text
    assert 'class="text-warning"' not in response.text
    assert 'class="text-danger"' not in response.text


def test_bien_id_turns_green_when_validated_present(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "Présent"}
    )

    response = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert 'class="text-success"' in response.text


def test_bien_id_turns_orange_when_validated_en_trop(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "En Trop"}
    )

    response = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert 'class="text-warning"' in response.text


def test_bien_id_turns_red_when_validated_absent(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "Absent"}
    )

    response = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert 'class="text-danger"' in response.text


def test_extra_line_bien_id_is_colored_immediately(client, admin_user):

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    response = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert 'class="text-success"' in response.text


def test_update_line_changes_statut_and_commentaire(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={
            "local": "SALLE 101",
            "statut": "Absent",
            "commentaire": "non trouvé lors du contrôle"
        },
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?local=SALLE%20101&updated=1"
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert "non trouvé lors du contrôle" in page.text


def test_update_line_sets_type_bien_on_known_asset(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Copieur"})
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={
            "local": "SALLE 101",
            "statut": "Présent",
            "type_bien_id": asset_type_id
        }
    )

    # Reflété sur l'Inventaire : une seule valeur partagée, pas une
    # copie propre à la ligne de suivi.
    inventaire_page = client.get("/assets")

    assert re.search(
        r'value="' + asset_type_id + r'"\s*selected', inventaire_page.text
    )

    local_page = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert re.search(
        r'value="' + asset_type_id + r'"\s*selected', local_page.text
    )


def test_update_line_sets_type_bien_on_extra_line(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Caisson"})

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={
            "local": "SALLE 101",
            "statut": "Présent",
            "type_bien_id": asset_type_id
        }
    )

    local_page = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert re.search(
        r'value="' + asset_type_id + r'"\s*selected', local_page.text
    )


def test_update_line_rejects_invalid_statut(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "Perdu"}
    )

    assert response.status_code == 400
    assert "invalide" in response.text


def test_update_missing_line_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/lines/999/update",
        data={"local": "SALLE 101", "statut": "Absent"}
    )

    assert response.status_code == 404


def test_delete_extra_line_removes_it(client, admin_user):

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/delete",
        data={"local": "SALLE 101"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?local=SALLE%20101&deleted=1"
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    assert "EXTRA1" not in page.text


def test_delete_known_line_is_rejected(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/delete",
        data={"local": "SALLE 101"}
    )

    assert response.status_code == 400
    assert "en trop" in response.text


def test_delete_missing_line_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/lines/999/delete",
        data={"local": "SALLE 101"}
    )

    assert response.status_code == 404


def test_validate_known_asset_line_sets_statut_present(client, admin_user):

    _login(client)

    _mark_line(client, "SALLE 101", "10001", "PC Portable", "Absent")

    page = client.get(
        "/inventaire-local", params={"statut_filter": "Absent"}
    )

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/validate')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/validate",
        data={"statut_filter": "Absent"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?statut_filter=Absent&validated=1"
    )

    response = client.get(
        "/inventaire-local", params={"statut_filter": "Absent"}
    )

    assert "10001" not in response.text

    # Toujours visible sur l'onglet Par local, désormais Présent.
    local_page = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert "10001" in local_page.text


def test_validate_extra_line_deletes_it(client, admin_user):

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get(
        "/inventaire-local", params={"statut_filter": "En Trop"}
    )

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/validate')[0]

    response = client.post(
        f"/inventaire-local/lines/{line_id}/validate",
        data={"statut_filter": "En Trop"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/inventaire-local?statut_filter=En%20Trop&validated=1"
    )

    response = client.get(
        "/inventaire-local", params={"statut_filter": "En Trop"}
    )

    assert "EXTRA1" not in response.text

    # Supprimée entièrement (pas juste sortie du filtre) : absente
    # aussi de l'onglet Par local de ce local.
    local_page = client.get(
        "/inventaire-local", params={"local": "SALLE 101"}
    )

    assert "EXTRA1" not in local_page.text


def test_validate_missing_line_returns_404(client, admin_user):

    _login(client)

    response = client.post(
        "/inventaire-local/lines/999/validate",
        data={"statut_filter": "Absent"}
    )

    assert response.status_code == 404


def test_validate_line_requires_manager_role(client, standard_user):

    _login_reader(client)

    response = client.post(
        "/inventaire-local/lines/1/validate",
        data={"statut_filter": "Absent"}
    )

    assert response.status_code == 403


def test_export_csv_includes_known_and_extra_lines(client, admin_user):

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    client.post(
        "/inventaire-local/add",
        data={
            "local": "SALLE 101",
            "bien_id": "EXTRA1",
            "commentaire": "trouvé sur place"
        }
    )

    response = client.get(
        "/inventaire-local/export-csv", params={"local": "SALLE 101"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == "Bien ID;Désignation;Type de bien;Commentaire;Statut"
    assert "10001;PC Portable;;;Présent" in lines
    assert "EXTRA1;;;trouvé sur place;Présent" in lines


def _line_id_for_bien(page_text, bien_id):
    """
    Extrait l'id de ligne associé à un Bien ID précis (et non le
    premier de la page) : nécessaire dès qu'un local affiche plusieurs
    biens, triés par Bien ID, pour ne pas mettre à jour la mauvaise
    ligne.
    """

    position = page_text.index(bien_id)

    match = re.search(
        r'/inventaire-local/lines/(\d+)/update', page_text[position:]
    )

    return match.group(1)


def _mark_line(client, local, bien_id, designation, statut, commentaire=""):

    _import_asset(client, bien_id, designation, local)

    page = client.get("/inventaire-local", params={"local": local})

    line_id = _line_id_for_bien(page.text, bien_id)

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": local, "statut": statut, "commentaire": commentaire}
    )


def test_biens_a_traiter_tab_shows_filter_options(client, admin_user):

    _login(client)

    response = client.get("/inventaire-local")

    assert "Biens à traiter" in response.text
    assert "Absent" in response.text
    assert "En Trop" in response.text


def test_biens_a_traiter_shows_no_table_without_filter(client, admin_user):

    _login(client)

    response = client.get("/inventaire-local")

    assert "Aucun bien à ce statut." not in response.text


def test_statut_filter_lists_absent_biens_across_locals(client, admin_user):

    _login(client)

    _mark_line(client, "SALLE 101", "10001", "PC Portable", "Absent")
    _mark_line(client, "SALLE 202", "20002", "Ecran", "Absent")
    _mark_line(client, "SALLE 101", "10003", "Imprimante", "Présent")

    response = client.get(
        "/inventaire-local", params={"statut_filter": "Absent"}
    )

    assert response.status_code == 200
    assert "10001" in response.text
    assert "20002" in response.text
    assert "10003" not in response.text
    assert "SALLE 101" in response.text
    assert "SALLE 202" in response.text


def test_statut_filter_lists_en_trop_biens(client, admin_user):

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "En Trop"}
    )

    response = client.get(
        "/inventaire-local", params={"statut_filter": "En Trop"}
    )

    assert "EXTRA1" in response.text


def test_statut_filter_en_trop_shows_extra_regardless_of_statut(
    client, admin_user
):
    """
    Un bien "en trop" reste à reporter dans le logiciel de gestion
    d'inventaire externe tant qu'il n'y figure pas, indépendamment de
    son statut lors du contrôle — il doit donc apparaître dans le
    filtre "En Trop" même sans jamais avoir été marqué à ce statut
    (par défaut "Présent" à l'ajout, voir add_extra_line).
    """

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    response = client.get(
        "/inventaire-local", params={"statut_filter": "En Trop"}
    )

    assert "EXTRA1" in response.text
    assert "SALLE 101" in response.text


def test_statut_filter_en_trop_shows_known_asset_marked_en_trop(
    client, admin_user
):

    _login(client)

    _mark_line(client, "SALLE 101", "10001", "PC Portable", "En Trop")

    response = client.get(
        "/inventaire-local", params={"statut_filter": "En Trop"}
    )

    assert "10001" in response.text


def test_statut_filter_en_trop_excludes_extra_marked_absent_from_absent_filter_only(
    client, admin_user
):
    """
    Un bien "en trop" marqué Absent apparaît dans le filtre En Trop
    (toujours "à traiter") ET dans le filtre Absent (pour repérer les
    biens qu'on ne retrouve plus).
    """

    _login(client)

    client.post(
        "/inventaire-local/add",
        data={"local": "SALLE 101", "bien_id": "EXTRA1"}
    )

    page = client.get("/inventaire-local", params={"local": "SALLE 101"})

    line_id = page.text.split(
        '/inventaire-local/lines/'
    )[1].split('/update')[0]

    client.post(
        f"/inventaire-local/lines/{line_id}/update",
        data={"local": "SALLE 101", "statut": "Absent"}
    )

    en_trop_response = client.get(
        "/inventaire-local", params={"statut_filter": "En Trop"}
    )
    absent_response = client.get(
        "/inventaire-local", params={"statut_filter": "Absent"}
    )

    assert "EXTRA1" in en_trop_response.text
    assert "EXTRA1" in absent_response.text


def test_statut_filter_does_not_create_lines(client, admin_user):
    """
    Contrairement à l'onglet Par local, l'onglet Biens à traiter ne
    doit jamais créer de ligne automatiquement : les biens actifs d'un
    local jamais consulté ne doivent pas apparaître comme "Absent" par
    défaut.
    """

    _login(client)
    _import_asset(client, "10001", "PC Portable", "SALLE 101")

    response = client.get(
        "/inventaire-local", params={"statut_filter": "Absent"}
    )

    assert "10001" not in response.text


def test_biens_a_traiter_denies_reader_role(client, standard_user):

    _login_reader(client)

    response = client.get(
        "/inventaire-local", params={"statut_filter": "Absent"}
    )

    assert response.status_code == 403


def test_export_csv_statut_includes_expected_columns(client, admin_user):

    _login(client)

    client.post("/admin/asset-types", data={"libelle": "Copieur"})

    asset_type_id = client.get(
        "/admin/destinations"
    ).text.split('/admin/asset-types/')[1].split('/update')[0]

    _mark_line(
        client, "SALLE 101", "10001", "PC Portable", "Absent",
        commentaire="non retrouvé"
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
        f"/assets/{asset_id}/type-bien",
        data={"type_bien_id": asset_type_id}
    )

    response = client.get(
        "/inventaire-local/export-csv-statut", params={"statut": "Absent"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")

    lines = response.text.strip("\n").split("\n")

    assert lines[0] == (
        "Local;Bien ID;Désignation;Type de bien;Commentaire;Statut"
    )
    assert "SALLE 101;10001;PC Portable;Copieur;non retrouvé;Absent" in lines


def test_export_csv_statut_rejects_invalid_statut(client, admin_user):

    _login(client)

    response = client.get(
        "/inventaire-local/export-csv-statut", params={"statut": "Présent"}
    )

    assert response.status_code == 400


def test_export_csv_statut_requires_manager_role(client, standard_user):

    _login_reader(client)

    response = client.get(
        "/inventaire-local/export-csv-statut", params={"statut": "Absent"}
    )

    assert response.status_code == 403
