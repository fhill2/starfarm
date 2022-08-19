import subprocess, os
from globals import REPO_DIR
def replace_all(text, list):
    for s in list:
        text = text.replace(s, "")
    return text

def run_sh(cmd):
    output = subprocess.run(cmd, capture_output=True, shell=True)
    return output.stdout.decode('utf-8').strip().split("\n")


def symlink(source, dest):
    try:
        os.symlink(source, dest)
    except:
        pass

def url_to_full_name(url):
    if url.startswith("https://github.com/"):
        url = url.replace("https://github.com/", "")
    elif url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "")

    if url.endswith(".git"):
        url = url[0:-4]

    return url

def abs_to_sub(abs, owner, name):
    pList = abs.replace(REPO_DIR + "/", "").split("/") 
    sub = ""
    i=0
    for p in pList:
        if p.lower() == owner.lower() or p.lower() == name.lower(): 
            break

        if i==0:
            sub = p
        else:
            sub = sub + "/" + p
        i=i+1
    return sub

def remove_empty_folders(root):
    dirs = [name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name))]
    for dir in dirs:
        sub = os.path.join(root, dir)
        if not os.listdir(sub):
            os.rmdir(sub)
            print("- removing empty folder: " + sub)
