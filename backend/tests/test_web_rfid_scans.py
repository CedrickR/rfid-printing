def _login(client):

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )


def _upload_sample(client):

    csv_content = (
        "L26100000001;26120260001\n"
        "L26100000002;26120260002\n"
        "BADROW;xyz\n"
    )

    return client.post(
        "/rfid-scans",
        files={"file": ("scan.csv", csv_content, "text/csv")},
        follow_redirects=False
    )


def test_rfid_scans_page_requires_login(client):

    response = client.get("/rfid-scans", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")


def test_upload_redirects_to_detail_with_invalid_count(client, admin_user):

    _login(client)

    response = _upload_sample(client)

    assert response.status_code == 303
    assert response.headers["location"] == "/rfid-scans/1?invalid=1"


def test_upload_rejects_non_csv_file(client, admin_user):

    _login(client)

    response = client.post(
        "/rfid-scans",
        files={"file": ("scan.txt", "L26100000001;26120260001\n", "text/plain")}
    )

    assert response.status_code == 400
    assert "CSV" in response.text


def test_upload_shows_error_when_no_valid_line(client, admin_user):

    _login(client)

    response = client.post(
        "/rfid-scans",
        files={"file": ("scan.csv", "BADROW;xyz\n", "text/csv")}
    )

    assert response.status_code == 400
    assert "préfixes" in response.text.lower() or "aucune ligne" in response.text.lower()


def test_scan_list_shows_uploaded_file_and_line_count(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.get("/rfid-scans")

    assert response.status_code == 200
    assert "scan.csv" in response.text


def test_scan_detail_shows_parsed_lines(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.get("/rfid-scans/1")

    assert response.status_code == 200
    assert "00000001" in response.text
    assert "20260001" in response.text


def test_scan_detail_missing_file_returns_404(client, admin_user):

    _login(client)

    response = client.get("/rfid-scans/999")

    assert response.status_code == 404


def test_add_line(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.post(
        "/rfid-scans/1/lines",
        data={"lieu_numero": "00000003", "bien_id": "20260003"},
        follow_redirects=False
    )

    assert response.status_code == 303

    detail = client.get("/rfid-scans/1")
    assert "00000003" in detail.text
    assert "20260003" in detail.text


def test_add_line_rejects_empty_fields(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.post(
        "/rfid-scans/1/lines",
        data={"lieu_numero": "  ", "bien_id": "20260003"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert "error=missing_fields" in response.headers["location"]


def test_edit_line(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.post(
        "/rfid-scans/1/lines/1",
        data={"lieu_numero": "00000099", "bien_id": "20260099"},
        follow_redirects=False
    )

    assert response.status_code == 303

    detail = client.get("/rfid-scans/1")
    assert "00000099" in detail.text
    assert "20260099" in detail.text
    assert "00000001" not in detail.text


def test_edit_line_wrong_scan_file_returns_404(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.post(
        "/rfid-scans/999/lines/1",
        data={"lieu_numero": "00000099", "bien_id": "20260099"}
    )

    assert response.status_code == 404


def test_delete_line(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.post(
        "/rfid-scans/1/lines/1/delete",
        follow_redirects=False
    )

    assert response.status_code == 303

    detail = client.get("/rfid-scans/1")
    assert "00000001" not in detail.text
    assert "00000002" in detail.text


def test_export_returns_csv_with_timestamped_filename(client, admin_user):

    _login(client)
    _upload_sample(client)

    response = client.get("/rfid-scans/1/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "export_rfid_" in response.headers["content-disposition"]
    assert "L26100000001;26120260001" in response.text
    assert "L26100000002;26120260002" in response.text


def test_export_missing_file_returns_404(client, admin_user):

    _login(client)

    response = client.get("/rfid-scans/999/export")

    assert response.status_code == 404
