import libtmux
from auto_tmux import _get_full_path, load_layout
from tqdm.contrib.logging import logging_redirect_tqdm
from os.path import isfile
from libqtile.log_utils import logger


async def tmux_layout(name):
    """loads the layout"""
    logger.warning(f"name :  {name}")
    layout_path = _get_full_path(name)

    logger.warning(f"layout :  {layout_path}")
    if not isfile(layout_path):
        return "not a valid layout"
    
    server = libtmux.Server()
    layout = await load_layout(server, layout_path, progress_bar=False)

    return "loaded succefully"
