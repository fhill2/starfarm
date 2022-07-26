from shutil import which
from pathlib import Path
import subprocess
import os
home = str(Path.home())
# TODO: ALL GLOBALS MUST NOT END WITH A FORWARD/BACK SLASH
PLUGIN_DIR = os.path.join(home, ".local/share/nvim/site/pack/packer")
REPO_DIR = os.path.join(home, "repos")
STARFARM_DIR = os.path.join(REPO_DIR, "starfarm")
CONFIG_DIR = os.path.join(home, ".config", "starfarm")
# symlink only dirs
REPO_TAG_DIR = os.path.join(home, "repos-tags")
REPO_FLAT_DIR = os.path.join(home, "repos-flat")

# SCRIPT_DIR = Path( __file__ ).absolute().parent

def get_token():
    if which("pass") is not None:
        return subprocess.run(['pass', 'show', 'gh/starfarm-pat'], capture_output=True).stdout.decode('utf-8').strip()
    else:
        return "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

TOKEN = get_token()


