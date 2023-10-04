import discord
from discord.ext import commands
from libqtile.log_utils import logger
from os import remove as rm, symlink
from os.path import expanduser, islink, isfile
import shutil
from libqtile.command.client import InteractiveCommandClient
from .gen_keybinding_img import make_imgs
from .gen_keybinding_img import this_dir as img_dir
from .auto_desk_api import set_layout, send
from .tmux import tmux_layout
from ._discord import config, token
from functools import wraps
from . import WALLPAPER_PATH


COMMAND_PREFIX = "/"
# WALLPAPER_PATH = expanduser("~/.config/qtile/wallpaper")
_intents = discord.Intents.default()
_intents.message_content = True
CLIENT = commands.Bot(intents=_intents, command_prefix=COMMAND_PREFIX)


def admin_user(user):
    return user.id in config.get("discord").get("admins")


def admin_only(func):
    async def wrapper(*args, **kwargs):
        ctx = args[0]
        res = None
        # print(f"{args=}")

        if admin_user(ctx.author):
            res = await func(*args, **kwargs)
        else:
            await ctx.send("not an authorized user")

        return res

    return wrapper


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


@admin_only
@CLIENT.command(name="get-keybinds")
async def get_keybinds(ctx):
    """replies with the keyboard currently configured"""
    try:
        shutil.rmtree(img_dir)
    except FileNotFoundError:
        pass

    images = [discord.File(img) for img in make_imgs(config_path=expanduser("~/.config/qtile/config.py"))]
    await ctx.send(files=images)


@admin_only
@CLIENT.command(name="set-wallpaper")
async def set_wallpaper(ctx, path):
    """sets the Qtile wallpaper in a semi-permanent fassion"""
    # TODO: add ability to send an image via discord and have this function download it, 
    # save it to ~/.config/qtile/discord_wallpapers/image_name, save the image_name in a log,
    # and finally sent wallpaper to it.
    await ctx.send(f"setting walpaper to {path}")
    
    if islink(WALLPAPER_PATH) and isfile(expanduser(path)):
        rm(WALLPAPER_PATH)
        symlink(expanduser(path), WALLPAPER_PATH)
        ctx.send("set walpaper successfully.") 
    else:
        ctx.send("[FAILED] either the requested file doesn't exist, or the wallpaper is a file not a symlink. (more likely the former)")


@admin_only
@CLIENT.command(name="auto-desk")
async def set_desktop_layout(ctx, layout):
    """uses auto tmux to spin up a, auto-desk session"""
    await ctx.send(f"loading auto-desk layout {layout}")
    res = set_layout(layout)
    await ctx.send(f"auto-desk said: `{res}`")


@admin_only
@CLIENT.command(name="auto-tmux")
async def set_tmux_layout(ctx, layout):
    """uses auto tmux to spin up a tmux session"""
    await ctx.send(f"loading tmux layout {layout}")
    res = await tmux_layout(layout)
    await ctx.send(f"auto-tmux said: `{res}`")


@admin_only
@CLIENT.command(name="reload")
async def reload_config(ctx):
    """reloads the qtile configs"""
    c = InteractiveCommandClient()
    c.reload_config()

    await ctx.send("reloading configs")


@admin_only
@CLIENT.command(name="sleep")
async def sleep(ctx):
    """puts the computer to sleep"""
    import os

    await ctx.send("putting machine to sleep")
    os.system("systemctl suspend")


@admin_only
@CLIENT.command(name="open-on")
async def open_on(ctx, program: str, wm_class: str, desktop_name: str):
    """opens a .desktop file on a specific desktop"""
    # if ".desktop " not in cmd:
    #     await ctx.send("can't launch arbetrary files. must be a `.desktop` file")
    #     return
    #
    # desktop_file, tmp = cmd.split(".desktop ")
    # wm_class, desktop_name = tmp.split(" ")
    # if not admin_user(ctx.author):
        # wait ctx.send("not an authorized user")

    # if not program.endswith(".desktop"):
    #     await ctx.send("can't launch arbetrary files. must be a `.desktop` file")
    #     return
    
    res = send(f"open-on {program} {wm_class} {desktop_name}")

    await ctx.send(f"auto-desk said: {res}")


if __name__ == "__main__":
    bot_start()
