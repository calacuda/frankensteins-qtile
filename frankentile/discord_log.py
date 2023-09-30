import discord
import time
import json
import asyncio
import aiohttp
import requests
from discord.ext import commands
from discord import Client
from libqtile.log_utils import logger
from libqtile import hook
from enum import Enum
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
print(f"global: {CLIENT.status = }")
HANDLES = None


class QueueIter:
    """an iterable wrapper arrounf multiprocessing.Queue"""
    def __init__(self, queue: Queue):
        self.queue = queue  # queue if queue else []

    def append(self, element):
        """add an element to the queue"""
        self.queue.put(element)

    def __repr__(self):
        return self.__str__()
        
    def __str__(self):
        return str(self.queue)

    def __bool__(self):
        return not self.queue.empty()

    def __len__(self):
        return len(self.queue)

    def __iter__(self):
        return self

    def __next__(self):
        if self:
            return self.queue.get()
        else:
            raise StopIteration


class Sender:
    """a state machine that stores messages to be sent to the discord server and sends them on regular intervals"""
    def __init__(self):
        self.connected = False
        self.queue = None
    
    def is_connected(self):
        """returns true if the bot is connected"""
        return self.connected

    async def _send_one(self, session, headers, payload, url):
        """helper function that sends a single message. called by send_all."""
        async with session.post(url, headers=headers, data=payload) as res:
            text = await res.text()

            if res.status != 200:
                logger.warning(f"status: {res.status}, text: {text}")
            
    async def send_all(self):
        """sends all messages in the queue"""
        headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": f"FrankenTile (https://discord.com/developers/applications/1134144480979726446/information v0.1)",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as client:
            reqs = []
            
            for id, message in self.queue:
                url = f"https://discord.com/api/v10/channels/{id}/messages"
                payload = json.dumps( {"content": message} )
                reqs.append(self._send_one(client, headers, payload, url))

            await asyncio.gather(*reqs)

    async def try_send_all(self, client, message: (int, str) = None):
        """trys to send messages, if not connected the messages get dumped in the queue"""
        if message:
            self.add_message(message[0], message[1])

        if self.connected:
            await self._send_all(client)

    async def init_sender(self, queue):
        self.queue = QueueIter(queue)

        while True:
            if self.queue:
                await self.send_all()

            await asyncio.sleep(2.5)


MESSENGER = Sender()
QUEUE = Queue()


def init_sender(queue):
    """waits for the bot to be connected and then starts sending messages in an iterval"""
    asyncio.run(MESSENGER.init_sender(queue))


def read_conf():
    """reads the config containing tokens and other information"""
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


config = read_conf()
token = config.get("discord").get("token")


class EventType(str, Enum):
    group_switch = "group_switch"
    focus_change = "focus_change"
    window_closed = "window_closed"
    new_window = "new_window"
    restart = "restart"
    resume = "resume"
    mon_change = "mon_change"
    shutdown = "shutdown"
    initial_start = "initial_start"
    booted = "booted"
    login = "login"
    volume = "volume"
    bat_low = "battery_low"
    bluetooth_status = "bluetooth_status"
    keyboard_attached = "keyboard_attached"
    mouse_attached = "mouse_attached"
    keyboard_detached = "keyboard_detached"
    mouse_detached = "mouse_detached"


def bot_start():
    logger.warning("starting discord command bot")
    
    try:
        CLIENT.run(token)
    except Exception as e:
        logger.warning(f"failed to start discord command bot. got error: {e}")
        print(e)


async def send_log(id: int, event_type: EventType, payload: dict):
    """sends a time stamped log to the channel described by id"""
    try:
        text_msg = json.dumps(
            {"timestamp": time.time(), "event_type": event_type, "payload": payload if payload else None}
        )
    except TypeError as e:
        text_msg = f"JSON encoding error: {e}"
        logger.error(f"frankentile error in frankentil.discord.send_log(). {text_msg}")

    await send_mesg(id, text_msg)


async def send_mesg(id: int, mesg: str):
    """sends a timestamped message to the channel described by id"""
    # logger.warning(f"adding to queue {(id, mesg)}")
    QUEUE.put((id, mesg))


async def log(event_type: EventType, payload: dict):
    """generic log function bc many hooks have similar code"""
    try:
        id = config.get("discord").get("log-channel")
    except TypeError as e:
        logger.error(f"could not find log cahnnel id in config file. expected at: \"discord.log-channel\". got error: {e}")
    else:
        await send_log(id, event_type, payload)


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


# @CLIENT.command(name="set-layout")
# async def set_layout(ctx, layout):
#     """uses auto-desk to set the layout"""
#     await ctx.send(f"attempting to set layout {layout} using auto-desk...")
#     # TODO: send layout-load cmd over Unix socket to auto-desk
#     res = set_layout(layout)
#     await ctx.send(f"setup layout {layout}. auto-desk says {res}")


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
async def set_wallpaper(ctx, layout):
    """uses auto tmux to spin up a, auto-desk session"""
    await ctx.send(f"loading auto-desk layout {layout}")
    res = set_layout(layout)
    await ctx.send(f"auto-desk said: `{res}`")


@CLIENT.command(name="auto-tmux")
async def set_wallpaper(ctx, layout):
    """uses auto tmux to spin up a tmux session"""
    await ctx.send(f"loading tmux layout {layout}")
    res = await tmux_layout(layout)
    await ctx.send(f"auto-tmux said: `{res}`")


async def closed_window(win):
    """
    Called after a client has been unmanaged
    (when the window is closed by the user.
    """
    await log(
        EventType.window_closed,
        {"name": win.name, "wm_class": win.get_wm_class(), "pid": win.get_pid()}
    )


async def new_window(win):
    """Called after Qtile starts managing a new client."""
    await log(
        EventType.new_window,
        {"name": win.name, "wm_class": win.get_wm_class(), "pid": win.get_pid()}
    )


async def restart():
    """
    Called before Qtile is restarted.
    (hopefully this includes when the device goes to sleep)
    """
    await log(EventType.restart, {})


async def resume():
    """Called when system wakes up from sleep, suspend or hibernate."""
    await log(EventType.resume, {})


async def monitor_change():
    """Called when the output configuration is changed (e.g. via randr in X11)."""
    await log(EventType.mon_change, {})


async def shutdown():
    """Called before Qtile is shutdown"""
    # logger.warning("shutting down")
    await log(EventType.shutdown, {})
    # await kill_bot()


async def start_success():
    """Called when Qtile is started after all resources initialized"""
    await log(EventType.booted, {"message": "Qtile configured successfully"})


async def login():
    """Called when Qtile has started on first start"""
    await log(EventType.login, {"message": "Welcome to Qtile!"})


async def kill_bot():
    """ensures that the bots stop running when the qtile does."""
    logger.info("stopping client bot") 
    await CLIENT.close()


def run_discord_bot():
    """runs the discord bot in parallel""" 
    handles = [
        Process(target=init_sender, args=[QUEUE]),
        Process(target=bot_start, args=()),
    ]

    [h.start() for h in handles]
    
    return handles


def start_discord_bot():
    """starts the discord bot on login"""
    global HANDLES
    HANDLES = run_discord_bot()


async def stop_discord_bot():
    """stops the discord bot on logout."""
    await kill_bot()
    global HANDLES
    [h.terminate() for h in HANDLES]


async def init_logger():
    await MESSENGER.init_sender(QUEUE)
    

def init():
    """initializes the discord api. should be called from Qtile's main config.py"""
    # activate/deactivate bot
    if config.get("discord").get("api"):
        hook.subscribe.startup_once(start_discord_bot)
        hook.subscribe.shutdown(stop_discord_bot)
    else:
        hook.subscribe.startup_once(init_logger)

    # logging functionality
    hook.subscribe.client_killed(closed_window)
    hook.subscribe.client_managed(new_window)
    hook.subscribe.restart(restart)
    hook.subscribe.resume(resume)
    hook.subscribe.screen_change(monitor_change)
    hook.subscribe.shutdown(shutdown)
    hook.subscribe.startup_complete(start_success)
    hook.subscribe.startup_once(login)


if __name__ == "__main__":
    bot_start()
