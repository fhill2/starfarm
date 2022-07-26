import os, yaml, emoji, git, subprocess
from globals import TOTAL_STEPS, SCRIPT_DIR, REPO_DIR, PLUGIN_DIR, STARFARM_DIR, REPO_TAG_DIR, REPO_FLAT_DIR, TOKEN

from ghapi.all import GhApi, pages, paged
api = GhApi(token=TOKEN)
import concurrent



def remove_empty_folders(root):
    dirs = [name for name in os.listdir(root) if os.path.isdir(os.path.join(root, name))]
    for dir in dirs:
        sub = os.path.join(root, dir)
        if not os.listdir(sub):
            os.rmdir(sub)
            print("- removing empty folder: " + sub)
def mkdir(path):
    try:
        os.mkdir(path, mode = 0o777)
    except:
        pass

# def symlink(source, dest):
#     try:
#         os.symlink(source, dest)
#     except:
#         pass

def find_repo_source(all_repos, match_repo):
    repo = lookup_by_fullname(all_repos, match_repo["full_name"])
    print(repo["cat"])
    if repo["cat"].startswith("packer"):
        return os.path.join(REPO_DIR, repo["cat"], plugin_repo["name_nolower"])
    else: 
        return os.path.join(REPO_DIR, repo["cat"], plugin_repo["name"])



def find_repo_category(relpath):
    # accepts relpath from REPO_DIR
    # TODO; could find this dynamically - walk folder structure, ist non git folders
    categories = [ "git", "packer-fork", "packer/start", "packer/opt", "starfarm" ]
    for cat in categories:
        if relpath.startswith(cat):
            return cat.replace("/", "_")


def get_all_repos():
    # retrieves all repos under REPO_DIR
    all_repos = subprocess.run(["starfarm_find_git_repos " + REPO_DIR], capture_output=True, shell=True).stdout.decode('utf-8').strip().split("\n")
    repos = []

    for abs in all_repos:
        repo = repo_from_path(abs)
        repo["cat"] = find_repo_category(os.path.relpath(abs, REPO_DIR))
        repo["abs"] = abs
        repos.append(repo)
    return repos



    

def repo_from_path(path):
    # local abs path only
    full_name = git.Repo(path).remotes.origin.url.replace("https://github.com/", "").replace("git@github.com:", "").replace(".git", "").lower()
    owner_name = full_name.split("/")
    return {
        "owner": owner_name[0],
        "name": owner_name[1],
        "full_name": full_name,
    }


def get_flat_repos():
    repos = []
    for filename in os.listdir(REPO_FLAT_DIR):
        if os.path.exists(os.readlink(os.path.join(REPO_FLAT_DIR, filename))):
            filenameList = filename.split("|")
            repos.append({
                "cat": filenameList[0],
                "owner": filenameList[1],
                "name": filenameList[2],
                "full_name": "/".join([filenameList[-2], filenameList[-1]]),
                "filename": filename
                })
        # abs = os.path.join(REPO_DIR, repo.replace("|", "/"))
        # repos.append(repo_from_path(abs))
    return repos




def get_stars(stars):
    # https://github.com/fastai/ghapi/issues/36
    repos_first_page  = api.activity.list_repos_starred_by_authenticated_user()
    repos = pages(api.activity.list_repos_starred_by_authenticated_user, api.last_page()).concat()
    # stars = []
    for repo in repos:
        full_name = repo["full_name"].lower()
        owner_name = full_name.split("/")
        stars.append({
            "owner": owner_name[0],
            "name": owner_name[1],
            "full_name": full_name 
        })



def lookup_by_fullname(repos, full_name):
    for repo in repos:
        if repo["full_name"] == full_name:
            return repo
    return False



def filter_by_fullname(a, b):
    # filters b from a, using the full_name key
    blist = [bb["full_name"] for bb in b]
    def should_filter(repo):
        bool = True if repo["full_name"] not in blist else False
        return bool

    return list(filter(should_filter, a))

def filter_by_fullname_tag(a, b):
    c = a.copy()
    for bb in b:
        for aa in a:
            if bb["full_name"] == aa["full_name"] and bb["tag"] == aa["tag"]:
                c.remove(aa)
    return c



def packer_repo_from_path(path):
    # local abs path only
    full_name = git.Repo(path).remotes.origin.url.replace("https://github.com/", "").replace("git@github.com:", "").replace(".git", "")
    owner_name = full_name.split("/")
    return {
        "owner": owner_name[0].lower(),
        "name": owner_name[1].lower(),
        "full_name": full_name.lower(),
        # packer installs plugins with upper and lowercase letters, and sees a lowercase named repo as a different plugin
        "name_nolower": owner_name[1]
    }

def get_packer():
        start_repos = [PLUGIN_DIR + "/start/" + plug for plug in os.listdir(PLUGIN_DIR + "/start")]
        opt_repos = [PLUGIN_DIR + "/opt/" + plug for plug in os.listdir(PLUGIN_DIR + "/opt")]

        repos = []
        for abs in start_repos:
            repo = packer_repo_from_path(abs)
            repo["sub"] = "start"
            repos.append(repo)
        for abs in opt_repos:
            repo = packer_repo_from_path(abs)
            repo["sub"] = "opt"
            repos.append(repo)


        return repos



# def packer_dirs_to_lower():
#     start_repos, opt_repos = get_packer_abs()
# # change all repos to lowercase
# os.chdir(os.path.join(PLUGIN_DIR, "start"))
# for name in os.listdir("."):
#     if any(char.isupper() for char in name):
#         os.rename(name, name.lower())
#
# os.chdir(os.path.join(PLUGIN_DIR, "opt"))
# for name in os.listdir("."):
#     if any(char.isupper() for char in name):
#         os.rename(name, name.lower())

# def get_packer():
#     def opt_start(opt_start):
#         folder = os.path.join(PLUGIN_DIR, opt_start)
#         dirs = [name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name))]
#         cmd_str = ""
#         for dir in dirs:
#             cmd_str += "cd " + dir + " && git config --get remote.origin.url && cd .. && "
#         cmd_str += "exit"
#         output = subprocess.run(["zsh", "-c", cmd_str], capture_output=True, cwd=folder).stdout.decode('utf-8')
#         return output.replace("https://github.com/", "").replace("git@github.com:", "").replace(".git", "")
#
#     # returns as repos = ["owner/repo", "owner/repo"]
#     repos = (opt_start("start") + opt_start("opt")).split("\n")
#
#     # remove empty strings in list
#     while ("" in repos):
#         repos.remove("")
#
#     plugins = []
#     for repo_str in repos:
#         repo_str = repo_str.lower()
#         owner_name = repo_str.split("/")
#         plugins.append({
#             'owner': owner_name[0],
#             'name': owner_name[1],
#             'full_name': repo_str
#         })
#     return plugins


def get_org(org):
    """Gets all repos under an organization. Used for get_config *"""
    """['owner_name', 'owner_name']"""
    repos = paged(api.repos.list_for_org, org=org)
    org_repos = []
    for page in repos:
        for repo in page:
            org_repos.append(repo["full_name"].lower())
    return org_repos

def per_repo(repo, tag=False): 
    owner_name = repo.lower().split("/")
    repo_dict = {
            'owner': owner_name[0],
            'name' : owner_name[1],
            'full_name' : repo.lower(),
            'tag': "unsorted"
        }
    if tag:
        repo_dict["star"] = True if "*" not in tag else False
        repo_dict["tag"] = tag.replace("*", "")
    return repo_dict


def get_unsorted():
    with open(os.path.join(SCRIPT_DIR, 'tags_unsorted.yaml')) as f:
        tags_unsorted_file = yaml.safe_load(f)
    if tags_unsorted_file == None:
        tags_unsorted_file = []
    repos = []
    for repo in tags_unsorted_file:
        if repo is None:
            continue
        repos.append(per_repo(repo))
    return repos


def get_config():
    with open(os.path.join(SCRIPT_DIR, 'tags.yaml')) as f:
        tags_file = yaml.safe_load(f)

    if tags_file == None:
        tags_file = []

    repos = []
    for tag in tags_file:
        for repo in tags_file[tag]:
            if repo is None:
                continue
            if "/" not in repo:
                for org_repo in get_org(repo):
                    tags_file[tag].append(org_repo)
                continue

            repos.append(per_repo(repo.lower(), tag))
    return repos

def get_syms():
    repos = []
    for tag in os.listdir(REPO_TAG_DIR):
        sub = os.path.join(REPO_TAG_DIR, tag)
        if os.path.isdir(sub):
            for repo in os.listdir(sub):
                if os.path.exists(os.readlink(os.path.join(sub, repo))):
                    if repo is not None:
                        owner_name = repo.split("|")
                        repos.append({
                            'owner': owner_name[0],
                            'name' : owner_name[1],
                            'full_name' : "/".join(owner_name),
                            'tag' : tag
                        })
    return repos



def get_fs():
    repos = []
    for owner in os.listdir(STARFARM_DIR):
        sub = os.path.join(STARFARM_DIR, owner)
        if os.path.isdir(sub):
            for repo in os.listdir(sub):
                repos.append({
                    'owner': owner,
                    'name' : repo,
                    'full_name' : owner + "/" + repo
                })
    return repos




def clone(repo):
    url = "https://github.com/" + repo["full_name"]
    dest = os.path.join(STARFARM_DIR, repo["full_name"])
    cmd = "git clone " + url + " " + dest + " --depth 1"
    print("+ " + cmd)
    git.Repo.clone_from(url, dest)



def clone_all(repos):
    remaining = len(repos)
    for repo in repos:
        mkdir(os.path.join(STARFARM_DIR, repo["owner"]))
        with concurrent.futures.ProcessPoolExecutor(max_workers=5) as executor:
            results = [executor.submit(clone,repo) for repo in repos]


def star(repo):
    print(emoji.emojize(":star:") + " " + repo["full_name"])
    try:
        api.activity.star_repo_for_authenticated_user(owner=repo["owner"], repo=repo["name"])
    except Exception as e: 
        print(emoji.emojize(":cross_mark:") + " Exception Encountered when starring: " + repo["full_name"] + " - does the repo exist?")
        # print(type(e))
        print(e)
        exit()

def steps(step):
    return str(step) + "/" + str(TOTAL_STEPS) + " "





    # abs = os.path.join(REPO_DIR, "/".join(relpathList))
 
        # else:
# def get_all_flat_repos():
#     for repo in get_all_repos():
#         gitRepo = git.Repo(repo)
#         print(gitRepo)
