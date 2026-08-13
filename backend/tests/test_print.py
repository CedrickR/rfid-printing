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


def _create_two_jobs_with_distinct_assets(client, token):
    """
    Crée deux lots distincts, chacun avec un seul bien d'identifiant
    différent, pour tester la recherche de lots par Bien ID.
    """

    csv_content = (
        "numero;libelle;sortie\n"
        "10001;PC Portable;\n"
        "20002;Ecran;\n"
    )

    client.post(
        "/api/import/",
        files={"file": ("inventaire.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"}
    )

    assets = {
        a["bien_id"]: a["id"]
        for a in client.get(
            "/api/import/assets",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
    }

    job_ids = {}

    for bien_id in ("10001", "20002"):

        job_response = client.post(
            "/api/print/jobs",
            json={"asset_ids": [assets[bien_id]]},
            headers={"Authorization": f"Bearer {token}"}
        )

        job_ids[bien_id] = job_response.json()["job_id"]

    return job_ids


def test_get_jobs_search_by_bien_id_filters_matching_job_only(
    client, admin_user
):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    job_ids = _create_two_jobs_with_distinct_assets(client, token)

    response = client.get(
        "/api/print/jobs",
        params={"bien_id": "10001"},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

    job_ids_in_result = {job["id"] for job in response.json()}

    assert job_ids_in_result == {job_ids["10001"]}


def test_get_jobs_search_by_bien_id_supports_partial_match(
    client, admin_user
):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    job_ids = _create_two_jobs_with_distinct_assets(client, token)

    response = client.get(
        "/api/print/jobs",
        params={"bien_id": "2000"},
        headers={"Authorization": f"Bearer {token}"}
    )

    job_ids_in_result = {job["id"] for job in response.json()}

    assert job_ids_in_result == {job_ids["20002"]}


def test_get_jobs_without_bien_id_filter_shows_everything(
    client, admin_user
):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    job_ids = _create_two_jobs_with_distinct_assets(client, token)

    response = client.get(
        "/api/print/jobs",
        headers={"Authorization": f"Bearer {token}"}
    )

    job_ids_in_result = {job["id"] for job in response.json()}

    assert job_ids_in_result == set(job_ids.values())


def test_web_jobs_page_search_by_bien_id(client, admin_user):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    job_ids = _create_two_jobs_with_distinct_assets(client, token)

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    response = client.get("/jobs", params={"bien_id": "10001"})

    assert response.status_code == 200
    assert "1 lot(s) trouvé(s)" in response.text
    assert f'/jobs/{job_ids["10001"]}' in response.text
    assert f'/jobs/{job_ids["20002"]}' not in response.text


def test_jobs_search_button_redirects_directly_to_matching_job(
    client, admin_user
):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    job_ids = _create_two_jobs_with_distinct_assets(client, token)

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    response = client.get(
        "/jobs/search",
        params={"bien_id": "20002"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == f'/jobs/{job_ids["20002"]}'


def test_jobs_search_button_redirects_to_most_recent_when_several_match(
    client, admin_user
):

    login = client.post(
        "/auth/login",
        json={"username": "admin", "password": "Admin123!"}
    )

    token = login.json()["access_token"]

    csv_content = "numero;libelle;sortie\n10001;PC Portable;\n"

    client.post(
        "/api/import/",
        files={"file": ("inventaire.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"}
    )

    asset_id = client.get(
        "/api/import/assets",
        headers={"Authorization": f"Bearer {token}"}
    ).json()[0]["id"]

    job_ids = []

    for _ in range(2):

        job_response = client.post(
            "/api/print/jobs",
            json={"asset_ids": [asset_id]},
            headers={"Authorization": f"Bearer {token}"}
        )

        job_ids.append(job_response.json()["job_id"])

    client.post(
        "/login",
        data={
            "username": "admin",
            "password": "Admin123!",
            "next": "/dashboard"
        }
    )

    response = client.get(
        "/jobs/search",
        params={"bien_id": "10001"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == f"/jobs/{max(job_ids)}"


def test_jobs_search_button_redirects_to_list_with_error_when_no_match(
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

    response = client.get(
        "/jobs/search",
        params={"bien_id": "99999999"},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == (
        "/jobs?bien_id=99999999&error=not_found"
    )

    page = client.get(response.headers["location"])

    assert "Aucun lot ne contient le Bien ID" in page.text


def test_jobs_search_button_without_bien_id_redirects_to_list(
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

    response = client.get("/jobs/search", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/jobs"