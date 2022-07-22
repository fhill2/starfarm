from shutil import which
from pathlib import Path
import subprocess
home = str(Path.home())
DEV = home + "/dev"
PLUGIN_DIR = home + "/.local/share/nvim/site/pack/packer"
REPO_DIR = home + "/repos/repodl"
REPO_SYM_DIR = home + "/repodl"
TOTAL_STEPS = 9

def get_token():
    if which("pass") is not None:
        return subprocess.run(['pass', 'show', 'gh/repodl-pat'], capture_output=True).stdout.decode('utf-8').strip()
    else:
        return "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

TOKEN = get_token()
