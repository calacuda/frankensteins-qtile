"""
a simple api for interacting with auto-desk
"""


from os.path import expanduser
import socket
import tomllib
import os


HOME = expanduser("~")
_CONF_FILE = f"{HOME}/.config/auto-desk/config.toml"
_LAYOUT_DIR = f"{HOME}/.config/auto-desk/layouts"


def configs():
    with open(_CONF_FILE, "rb") as f:
        data = tomllib.load(f)
        return data


def send(payload):
    path = configs().get("server").get("listen_socket")

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(path)
        s.send(payload.encode("ascii"))

        s.shutdown(1)
        res = s.recv(1024).decode('utf-8')

        return res


def set_layout(layout):
    payload = f"load-layout {layout}"
    return send(payload)


def _transform_layout_name(name):
    return name.lower().split(".")[0].replace(" ", "").replace("-", "").replace("_", "")


def find_layout_file(name):
    init_name = _transform_layout_name(name)
    # print(f"{init_name=}")
    # print(f"{os.listdir(_LAYOUT_DIR)}")
    layouts = [(_transform_layout_name(f_name), f_name) for f_name in os.listdir(_LAYOUT_DIR) if os.path.isfile(os.path.join(_LAYOUT_DIR, f_name))]
    
    for (layout, layout_name) in layouts:
        # print(f"{layout=}")
        if init_name == layout:
            return layout_name

    return ""

