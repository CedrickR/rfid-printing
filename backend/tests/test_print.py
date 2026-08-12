def test_get_jobs(client,
    admin_user):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/api/print/jobs",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 200


def test_get_unknown_job(
    client,
    admin_user
):

    login = client.post(
        "/auth/login",
        json={
            "username": "admin",
            "password": "Admin123!"
        }
    )

    token = login.json()["access_token"]

    response = client.get(
        "/api/print/jobs/99999",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert response.status_code == 404


def test_generate_print_job_file(
    client,
    admin_user
):

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

    import_response = client.post(
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

    assert import_response.status_code == 200

    assets_response = client.get(
        "/api/import/assets",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assets = assets_response.json()

    assert len(assets) > 0

    asset_id = assets[0]["id"]

    job_response = client.post(
        "/api/print/jobs",
        json={
            "asset_ids": [asset_id]
        },
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert job_response.status_code == 200

    job_id = job_response.json()["job_id"]

    generate_response = client.post(
        f"/api/print/jobs/{job_id}/generate",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert generate_response.status_code == 200

    data = generate_response.json()

    assert data["job_id"] == job_id
    assert data["status"] == "GENERATED"
    assert data["generated_file"] == f"print_job_{job_id}.cmd"


def test_get_generated_file(
    client,
    admin_user
):

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

    import_response = client.post(
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

    assert import_response.status_code == 200

    assets_response = client.get(
        "/api/import/assets",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert assets_response.status_code == 200

    assets = assets_response.json()

    assert len(assets) > 0

    asset_id = assets[0]["id"]

    job_response = client.post(
        "/api/print/jobs",
        json={
            "asset_ids": [asset_id]
        },
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert job_response.status_code == 200

    job_id = job_response.json()["job_id"]

    generate_response = client.post(
        f"/api/print/jobs/{job_id}/generate",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert generate_response.status_code == 200

    file_response = client.get(
        f"/api/print/jobs/{job_id}/file",
        headers={
            "Authorization":
                f"Bearer {token}"
        }
    )

    assert file_response.status_code == 200

    content = file_response.text

    assert "REM RFID PRINT JOB" in content
    assert "PRINT|bien_id=1001" in content