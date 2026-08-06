


def test_get_assets(client):

    response = client.get(
        "/api/import/assets"
    )

    assert response.status_code == 200