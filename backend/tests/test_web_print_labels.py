def _login(client, username="admin", password="Admin123!"):

    client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "next": "/dashboard"
        }
    )


def _seed_asset(client):

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie;local_numero\n"
                "20260001;PC Un;;01100021\n",
                "text/csv"
            )
        }
    )


def test_print_labels_requires_login(client):

    response = client.post("/assets/print-labels", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_print_labels_denies_reader_role(client, standard_user):

    _login(client, "employe", "Employe123!")

    response = client.post("/assets/print-labels", data={"asset_ids": ["1"]})

    assert response.status_code == 403


def test_print_labels_requires_selection(client, admin_user):

    _login(client)
    _seed_asset(client)

    response = client.post(
        "/assets/print-labels",
        data={},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/assets?error=no_selection"


def test_print_labels_shows_barcode_and_bien_id(client, admin_user):

    _login(client)
    _seed_asset(client)

    response = client.post(
        "/assets/print-labels",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 200
    assert '<svg id="barcode-1">' in response.text
    assert 'JsBarcode("#barcode-1", "20260001"' in response.text
    assert ">20260001<" in response.text


def test_print_labels_shows_destination_lettrine_and_location(
    client, admin_user
):

    _login(client)
    _seed_asset(client)

    client.post("/admin/destinations", data={"libelle": "Direction Info"})
    client.post(
        "/assets/1/destination",
        data={"destination": "Direction Info"}
    )

    client.post(
        "/admin/destinations/bureaux",
        files={
            "file": (
                "bureaux.csv",
                "codelieu;batiment;etage;bureau\n"
                "01100021;SIEGE;REZ DE CHAUSSEE;021-A\n",
                "text/csv"
            )
        }
    )

    response = client.post(
        "/assets/print-labels",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 200
    assert '<span class="lettrine">D</span>' in response.text
    assert '<span class="dest-rest">irection Info</span>' in response.text
    assert "REZ DE CHAUSSEE - 021-A" in response.text


def test_print_labels_handles_missing_destination_and_bureau(
    client, admin_user
):

    _login(client)
    _seed_asset(client)

    response = client.post(
        "/assets/print-labels",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 200
    assert '<span class="lettrine"></span>' in response.text


def test_print_labels_one_label_per_selected_asset(client, admin_user):

    _login(client)

    client.post(
        "/import",
        files={
            "file": (
                "inventaire.csv",
                "numero;libelle;sortie\n"
                "20260001;PC Un;\n"
                "20260002;PC Deux;\n",
                "text/csv"
            )
        }
    )

    response = client.post(
        "/assets/print-labels",
        data={"asset_ids": ["1", "2"]}
    )

    assert response.status_code == 200
    assert response.text.count('class="label"') == 2
    assert '<svg id="barcode-1">' in response.text
    assert '<svg id="barcode-2">' in response.text


def test_print_labels_page_size_is_90_by_36_mm(client, admin_user):

    _login(client)
    _seed_asset(client)

    response = client.post(
        "/assets/print-labels",
        data={"asset_ids": ["1"]}
    )

    assert response.status_code == 200
    assert "size: 90mm 36mm;" in response.text
