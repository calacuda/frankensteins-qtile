from os.path import expanduser
import tomllib


CONFIG_FILE = expanduser("~/.config/qtile/discord.toml")


def read_conf():
    """reads the config containing tokens and other information"""
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


config = read_conf()
token = config.get("discord").get("token")
