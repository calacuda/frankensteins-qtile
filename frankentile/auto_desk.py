#####################################
# Auto-Desk API stuff, helper hooks #
#####################################



from libqtile.command.client import InteractiveCommandClient
from libqtile.log_utils import logger
from libqtile import hook
from socket import socket, AF_UNIX, SOCK_STREAM


QTILE_CLIENT = InteractiveCommandClient()
NEW_CLIENT_PIDs = set()
PATH = "/tmp/desktop-automater"


def _open_on(client):
    """used to move windows when they open""" 
    pid = client.get_pid()

    # this function gets called twice per window opening.
    # bellow stops this function from moving windows that have already been moved.
    if pid not in NEW_CLIENT_PIDs:
        NEW_CLIENT_PIDs.add(pid)
        move_window(client)
    else:
        NEW_CLIENT_PIDs.remove(pid)


# @hook.subscribe.client_managed
async def open_on_backup(client):
    """
    used to move windows when the program sets its WM_CLASS after its managed (ie, after its registered)
    this was made bc spotify doesn't like playing nice with linux.

    this a back up for open_on().
    """
    # logger.warning("new client (from backup function)")
    _open_on(client)


# @hook.subscribe.client_new
async def open_on(client):
    """moves windows when they register"""
    # logger.warning("new client")
    _open_on(client)


# @hook.subscribe.group_window_add
async def clear_group(group, window):
    # logger.warning(f"clearing group \"{group.name}\"")
    clearing = should_clear(group.name)
    if clearing:
        logger.debug(f"clearing group {group.name}")
        pid = window.get_pid()
        for w in group.windows:
            if w.get_pid() != pid:
                w.togroup("hidden")


def get_location(wm_class):
    message = f"auto-move {wm_class[0]} {wm_class[1]}"
    return send_auto_desk(message)


def should_clear(group):
    message = f"should-clear {group}"
    res = send_auto_desk(message)
    logger.debug(f"should-clear res: '{res}'")
    return res == "true"


def send_auto_desk(message):
    """sends data to auto-desk and returns the response"""
    location = None

    with socket(AF_UNIX, SOCK_STREAM) as s:
        s.settimeout(10)
        try:
            s.connect(PATH)
        except FileNotFoundError:
            pass
        except TimeoutError:
            pass
        else:
            s.send(bytes(message, "utf-8"))
            s.shutdown(1)  # tells the server im done sending data and it can reply now.
            res = s.recv(1024)
            ec = res[0]
            if len(res) >= 3:
                location = res[2:].decode('utf-8')
            if ec:
                logger.error(f"got error code from auto-desk on message '{message}'.")

    return location


# untested
def clear_desktop(group):
    """clears all desktop in self.clears"""
    # for group in tmp_clears:
    if group:
        # windows = [w["id"]
                # for w in QTILE_CLIENT.windows() if w["group"] == group]
        windows = QTILE_CLIENT.group[group].windows()
        logger.info(f"about to clear windows from group '{group}'")
        for wid in windows:
            QTILE_CLIENT.window[wid].togroup("hidden")
        logger.info(f"cleared group '{group}'")
    else:
        logger.info(f"not clearing group '{group}'")            


def move_window(c):
    wm_class = c.get_wm_class()
    location = get_location(wm_class)
    logger.debug(f"moving to location, '{location}'")
    # clear = should_clear(location)
    # if clear:
    #     clear_desktop(location)
    if location:
        c.togroup(location)


def init():
    """intializes the auto-desk api. should be called once from Qtile's config.py"""
    hook.subscribe.client_new(open_on)
    hook.subscribe.client_managed(open_on_backup)
    hook.subscribe.group_window_add(clear_group)
