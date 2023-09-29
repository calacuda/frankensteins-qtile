"""
web_server.py

spins up a flask web server to host an api
"""


from flask import Flask, send_file
import zipfile 
import io
from .gen_keybinding_img import make_imgs 
from .gen_keybinding_img import this_dir as img_dir
from threading import Thread
import shutil
from multiprocessing import Process, Queue
from os.path import expanduser, islink
import os
from libqtile import hook
from libqtile.log_utils import logger


app = Flask("frankentile")
APP_HANDLE = None


@app.route("/key-binds", methods=["GET"])
def key_binds():
    """sends back a key bindings image"""
    try:
        shutil.rmtree(img_dir)
    except FileNotFoundError:
        pass

    images = make_imgs(config_path=expanduser("~/.config/qtile/config.py"))

    zip_f = os.path.join(img_dir, "keybinds.zip")

    with zipfile.ZipFile(zip_f, "w", zipfile.ZIP_DEFLATED, False) as zip_file:
        for fname in images:
            zip_file.writestr(fname.split("/")[-1], open(fname, "rb").read())

    return send_file(zip_f, download_name="keybinds.zip", as_attachment=True)


@app.route("/set-wallpaper", methods=["POST"])
def set_wallpaper():
    """takes either an image or a path to an image and setst the wallpaper to it"""
    # TODO: get image
    # TODO: set image sym link
    # TODO: reload configs
    return "<h1>UNDER CONSTRUCTION</h1>"


def _start_api(host, port):
    logger.warning("running web server")
    app.run(host=host, port=port)  # , debug=True, passthrough_errors=True, use_debugger=False, use_reloader=True)


def start_api(host="127.0.0.1", port=8080):
    """starts the flask server"""
    p = Process(target=_start_api, args=[host, port])
    p.start()
    global APP_HANDLE
    APP_HANDLE = p


def stop_api():
    if APP_HANDLE:
        APP_HANDLE.terminate()


def init():
    hook.subscribe.startup_once(start_api)
    hook.subscribe.shutdown(stop_api)


if __name__ == "__main__":
    start_api()
