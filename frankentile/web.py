"""
web_server.py

spins up a flask web server to host an api
"""


from flask import Flask, send_file, request
import zipfile 
import io
from .gen_keybinding_img import make_imgs 
from .gen_keybinding_img import this_dir as img_dir
from .discord_log import WALLPAPER_PATH
# from threading import Thread
import shutil
from multiprocessing import Process 
from os.path import expanduser, islink
import os
from libqtile import hook
from libqtile.log_utils import logger
from .auto_desk_api import set_layout
from os import remove as rm, symlink
from .tmux import tmux_layout
from libqtile.command.client import InteractiveCommandClient
import alsaaudio
from libqtile.command.base import SelectError, CommandError
from gi import require_version

require_version('Playerctl', '2.0')

from gi.repository import Playerctl, Gio
from gi.repository.GLib import GError


app = Flask("frankentile")
API_HANDLE = None


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


@app.route("/wallpaper", methods=["POST"])
def set_wallpaper():
    """takes a path to an image and sets the wallpaper to it"""
    path = request.values.get("wallpaper-path")

    if islink(WALLPAPER_PATH):
        rm(WALLPAPER_PATH)
        symlink(expanduser(path), WALLPAPER_PATH)

    # TODO: reload configs

    return "success"


@app.route("/auto-desk/layout/<layout>")
def load_layout(layout):
    """uses auto-desk to load the specified layout"""
    res = set_layout(layout)

    return f"setting auto-desk layout {layout}. auto-desk says: {res}"

@app.route("/auto-desk/open-on/<group>", methods=["POST"])
def open_on(group: str):
    """opens a .desktop file on group using auto-desk"""
    return "under construction"
    # TODO: get desktop file
    # TODO: launch desktop file on group with auto-desk 


@app.route("/tmux/<layout>")
async def tmux(layout):
    """sets up a tmux layout"""
    res = await tmux_layout(layout)

    return f"setting up auto-tmux layout {layout}. auto-tmux says: {res}"


@app.route("/focus-on/<group>")
def focus_on(group: str):
    """changes active focus to the specified group"""
    c = InteractiveCommandClient()
    
    try:
        c.group[group].toscreen()
    except SelectError:
        return "no group by that name"
    else:
        return "focus shifted"


@app.route("/move-to/<group>")
def move_to(group: str):
    """move current window to group"""
    c = InteractiveCommandClient()
    
    try:
        c.window.togroup(group)
    except CommandError:
        return "no group by that name"
    else:
        return "window moved" 


@app.route("/track/<control>")
def music(control: str):
    """used to control the music (play/pause/next/etc)"""
    player = Playerctl.Player()

    # TODO: make the play command open a player then play (if no player is open)

    controls = {
        "play": player.play, 
        "pause": player.pause,
        "play-pause": player.play_pause,
        "next": player.next,
        "prev": player.previous,
    }

    f = controls.get(control)

    if not f:
        return f"no track control command by the name \"{control}\" found. must be one of, {list(controls.keys())}"

    try:
        f()
    except GError:
        return "track control failed, is there a music player running?"
    else:
        return "track controlled succefully"


@app.route("/volume/<cmd>")
def volume(cmd):
    """adjusts volume"""
    m = alsaaudio.Mixer()
    vol = m.getvolume()
    vol = int(vol[0])
        
    volumes = {
        "up": vol + 5,
        "down": vol - 5,
        "mute": 0,
        }

    new_vol = volumes.get(cmd)

    if new_vol is None:
        return f"\"{cmd}\" is not a valid volume control command. please use one of {list(volumes.keys())}"

    m.setvolume(new_vol)
    return "volume adjusted correctly"


@app.route("/sleep")
def sleep():
    """puts the computer to sleep using systemctl"""
    import os

    os.system("systemctl suspend")


@app.route("/config-reload")
def config_reload():
    """reloads qtile configs"""
    c = InteractiveCommandClient()
    c.reload_config()

    return "configs reloaded succefully"


def start_app(host, port):
    logger.warning("running web server")
    app.run(host=host, port=port)  # , debug=True, passthrough_errors=True, use_debugger=False, use_reloader=True)


def start_api(host="127.0.0.1", port=8080):
    """starts the flask server"""
    p = Process(target=start_app, args=[host, port])
    p.start()
    global API_HANDLE
    API_HANDLE = p


def stop_api():
    if API_HANDLE:
        API_HANDLE.terminate()


def init():
    hook.subscribe.startup_once(start_api)
    hook.subscribe.shutdown(stop_api)


if __name__ == "__main__":
    start_app("127.0.0.1", 8080)
