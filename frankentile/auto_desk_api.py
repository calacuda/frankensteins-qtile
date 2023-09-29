"""
a simple api for interacting with auto-desk
"""


from os.path import expanduser
import socket
import tomllib


HOME = expanduser("~")
_CONF_FILE = f"{HOME}/.config/auto-desk/config.toml"


def configs():
    with open(_CONF_FILE, "rb") as f:
        data = tomllib.load(f)
        return data


def set_layout(layout):
    path = configs().get("server").get("listen_socket")

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(path)
        s.send(f"load-layout {layout}".encode("ascii"))

        s.shutdown(1)
        res = s.recv(1024).decode('utf-8')

        return res

