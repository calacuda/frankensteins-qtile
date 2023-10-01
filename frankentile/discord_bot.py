import discord
from discord.ext import commands
from discord import Client
from libqtile.log_utils import logger
from libqtile import hook
from os import remove as rm, symlink
from os.path import expanduser, islink
import tomllib
from multiprocessing import Process, Queue
import shutil
import os
from .gen_keybinding_img import make_imgs 
from .gen_keybinding_img import this_dir as img_dir
from .auto_desk_api import set_layout
from .tmux import tmux_layout


COMMAND_PREFIX = "/"
CONFIG_FILE = expanduser("~/.config/qtile/discord.toml")
WALLPAPER_PATH = expanduser("~/.config/qtile/wallpaper")
_intents = discord.Intents.default()
_intents.message_content = True
CLIENT = commands.Bot(intents=_intents, command_prefix=COMMAND_PREFIX)


def read_conf():
    """reads the config containing tokens and other information"""
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


config = read_conf()
token = config.get("discord").get("token")


def bot_start():
    logger.warning("starting discord command bot")
    
    try:
        CLIENT.run(token)
    except Exception as e:
        logger.error(f"failed to start discord command bot. got error: {e}")
        print(e)


@CLIENT.event
async def on_ready():
    msg = f'discord bot {CLIENT.user} is now running!'
    logger.info(msg)
    # print(msg)
    # await log(EventType.login, {"message": "Ready to log!"})


@CLIENT.command(name="get-keybinds")
async def get_keybinds(ctx):
    """replies with the keyboard currently configured""" 
    try:
        shutil.rmtree(img_dir)
    except FileNotFoundError:
        pass

    images = [discord.File(img) for img in make_imgs(config_path=expanduser("~/.config/qtile/config.py"))]
    await ctx.send(files=images)


@CLIENT.command(name="set-wallpaper")
async def set_wallpaper(ctx, path):
    """sets the Qtile wallpaper in a semi-permanent fassion"""
    # TODO: add ability to send an image via discord and have this function download it, 
    # save it to ~/.config/qtile/discord_wallpapers/image_name, save the image_name in a log,
    # and finally sent wallpaper to it.  

    await ctx.send(f"setting walpaper to {path}")
    
    if islink(WALLPAPER_PATH):
        rm(WALLPAPER_PATH)
        symlink(expanduser(path), WALLPAPER_PATH)
        ctx.send("set walpaper successfully.")


@CLIENT.command(name="auto-desk")
async def set_desktop_layout(ctx, layout):
    """uses auto tmux to spin up a, auto-desk session"""
    await ctx.send(f"loading auto-desk layout {layout}")
    res = set_layout(layout)
    await ctx.send(f"auto-desk said: `{res}`")


@CLIENT.command(name="auto-tmux")
async def set_tmux_layout(ctx, layout):
    """uses auto tmux to spin up a tmux session"""
    await ctx.send(f"loading tmux layout {layout}")
    res = await tmux_layout(layout)
    await ctx.send(f"auto-tmux said: `{res}`")


if __name__ == "__main__":
    bot_start()
