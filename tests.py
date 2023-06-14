import client
import server


def test_client_main_returns_null():
    assert client.main() == None


def test_server_main_returns_null():
    assert server.main() == None
