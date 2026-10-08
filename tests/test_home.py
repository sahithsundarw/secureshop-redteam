from app import HOST, create_app


def test_home_returns_200():
    client = create_app().test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"SecureShop" in response.data


def test_host_is_loopback_only():
    assert HOST == "127.0.0.1"
