import socket

import pytest

BLOCKED = "Red bloqueada en los tests"


def test_create_connection_to_a_real_host_is_blocked():
    with pytest.raises(RuntimeError, match=BLOCKED):
        socket.create_connection(("example.com", 80), timeout=5)


def test_name_resolution_is_blocked():
    with pytest.raises(RuntimeError, match=BLOCKED):
        socket.getaddrinfo("example.com", 80)


@pytest.mark.parametrize(
    ("family", "address"),
    [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")],
)
def test_connect_on_an_internet_socket_is_blocked(family, address):
    with (
        socket.socket(family, socket.SOCK_STREAM) as client,
        pytest.raises(RuntimeError, match=BLOCKED),
    ):
        client.connect((address, 9))


def test_local_unix_sockets_still_work():
    left, right = socket.socketpair()
    with left, right:
        left.sendall(b"ping")
        assert right.recv(4) == b"ping"
