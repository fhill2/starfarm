from globals import home, SCRIPT_DIR, PLUGIN_DIR, REPO_DIR, STARFARM_DIR, REPO_TAG_DIR, REPO_FLAT_DIR, TOKEN
import git, util, os, yaml, multiprocessing, time, shutil, emoji
from subprocess import run
from futil import dump

from ghapi.all import GhApi, pages, paged
api = GhApi(token=TOKEN)
import concurrent, subprocess
from concurrent.futures import ThreadPoolExecutor as Pool




class tagSym():
    def __init__(self, repo):
        self.filename = "|".join([repo.owner.lower(), repo.name.lower()])
        if repo.sub == "packer":
            self.update(tag=repo.sub)
        else:
            self.update(tag="unsorted")
        self.repo = repo


    def update(self, tag):
        self.sub = tag
        self.target = os.path.join(REPO_TAG_DIR, self.sub, self.filename)

class flatSym():
    def __init__(self, repo):
        self.filename = "|".join([repo.sub, repo.owner.lower(), repo.name.lower()])
        if repo.sub == "packer":
            self.sub = repo.sub
        self.repo = repo
        self.sub = repo.sub
        # self.source = repo.abs
        self.target = os.path.join(REPO_FLAT_DIR, self.filename)
        # self.exists = os.path.exists(self.target)


class Repo():
    def __init__(self, abs):
        if not abs.startswith(STARFARM_DIR):
            self.abs = os.path.join(STARFARM_DIR, abs)
        else:
            self.abs = abs
        self.source = os.path.realpath(abs)
        gitRepo = git.Repo(self.abs) 
        self.git = gitRepo
        self.full_name = util.url_to_full_name(gitRepo.remotes.origin.url)
        owner_name = self.full_name.split("/")
        self.owner = owner_name[0]
        self.name = owner_name[1]
        self.sub = util.abs_to_sub(self.abs, self.owner, self.name)
        self.starred = False
        self.restrict_star = False
        self.tagsym = tagSym(self)
        self.flatsym = flatSym(self)

    # def in_tags(self):
    #     return True if self.tagsym.sub != "unsorted" else False
    def update(self, tag):
        if "*" in tag:
            self.restrict_star = True
        self.tagsym.update(tag=tag)

    def symlink(self):
        for sym in [self.tagsym, self.flatsym]:
            try:
                os.symlink(self.source, sym.target)
            except:
                pass
            else:
                print("+ " + self.source + " --> " + sym.target)
        # return True if list(filter(lambda x: x.type == "tag", self.targets.values())) else False


def _clone_subprocess(full_name):
        repo = git.Repo.clone_from("https://github.com/" + full_name, os.path.join(STARFARM_DIR, full_name))
        while not repo:
            print("cloning..." + full_name)
            time.sleep(1)

def _download_stars_subprocess(stars):
    repos_first_page  = api.activity.list_repos_starred_by_authenticated_user()
    repos = pages(api.activity.list_repos_starred_by_authenticated_user, api.last_page()).concat()
    for repo in repos:
        stars.append(repo["full_name"].lower())


class Farm:
    def __init__(self):
        self.repos = {}
        # self.cloneList = [] # clones not yet started
        # self.clonesPending = []
        self.manager = multiprocessing.Manager()
        self.pool = Pool()
        self.downloading = []
        self.original_unsorted = []

        # TODO: make sure packer is symlinked here before get()
        for dir in [REPO_DIR, STARFARM_DIR, REPO_TAG_DIR, REPO_FLAT_DIR]:
            util.mkdir(dir)



    def _download_stars_json(self):
        self.stars = self.manager.list()
        p = multiprocessing.Process(target=_download_stars_subprocess, args=([self.stars]))
        p.start()
        return p.join


    def _get_all_repos(self):
        for abs in util.run_sh(["starfarm_find_git_repos " + REPO_DIR]): 
            # TODO: could create .ignore file in repo library to ignore certain workspaces
            # ignore git folder here
            if not os.path.relpath(abs, REPO_DIR).startswith("git"):
                repo = Repo(abs)
                self.repos[repo.full_name.lower()] = repo

    def _get_org(self, org):
        """Gets all repos under an organization. Used for get_config *"""
        """['owner_name', 'owner_name']"""
        repos = paged(api.repos.list_for_org, org=org)
        org_repos = []
        for page in repos:
            for repo in page:
                org_repos.append(repo["full_name"].lower())
        return org_repos

    def _load_yaml_file(self, path):
        with open(os.path.join(SCRIPT_DIR, path)) as f:
            file = yaml.safe_load(f)
        return file if file is not None else []

    def _get_download_tags(self):
        tags_file = self._load_yaml_file("tags.yaml") 
        repos = []
        for tag in tags_file:
            for full_name in tags_file[tag]:
                if full_name is None:
                    continue
                if "/" not in full_name:
                    for org_repo in self._get_org(full_name):
                        tags_file[tag].append(org_repo)
                    continue

                try:
                    repo = self.repos[full_name.lower()]
                except KeyError:
                    self._queue_repo_download(full_name, tag=tag)
                else:
                    repo.update(tag=tag)
                    


        return repos

    def _get_download_stars(self):
        for full_name in self.stars:
            if full_name in self.repos.keys():
                repo = self.repos[full_name]
                repo.starred = True 
            else:
                if full_name not in self.downloading:
                    self._queue_repo_download(full_name, star=True)


    def _queue_repo_download(self, full_name, tag=None, star=None):
        self.downloading.append(full_name.lower())
        url = "https://github.com/" + full_name
        dest = os.path.join(STARFARM_DIR, full_name)
        f = self.pool.submit(subprocess.call, f"git clone {url} {dest} --depth 1", shell=True)
        
        def on_complete(future):
            if future.exception() is not None:
                print("got exception: %s" % future.exception())
            else:
                print(f"finished downloading: {full_name}")
            repo = Repo(full_name)
            self.repos[full_name] = repo
            if tag:
                repo.update(tag=tag)
                
            if star:
                repo.starred = True
            repo.symlink()
            self.downloading.remove(full_name.lower())
        f.add_done_callback(on_complete)

    def _get_unsorted(self):
        for full_name in self._load_yaml_file("tags_unsorted.yaml"):
            if full_name is not None:
                self.original_unsorted.append(full_name.lower())
                self.repos[full_name.lower()].update(tag="unsorted")



    def _clean_flat_syms(self):
        for filename in os.listdir(REPO_FLAT_DIR):
            filenameList = filename.split("|")
            full_name = "/".join([filenameList[-2], filenameList[-1]])
            if full_name not in self.repos:
                abs = os.path.join(REPO_FLAT_DIR, filename)
                os.remove(abs)
                print("- Removing symlink: " + abs)

    def _clean_tag_syms(self):
        for rel in util.run_sh(["cd " + REPO_TAG_DIR + " && fd --type=l"]): 
            full_name = os.path.basename(rel).replace("|", "/")
            if full_name not in self.repos:
                 abs = os.path.join(REPO_TAG_DIR, rel)
                 os.remove(abs)
                 print("- Removing symlink: " + abs)




    def _write_tags_unsorted(self):
        full_names = []

        for [full_name, repo] in self.repos.items():
            tag = repo.tagsym.sub
            if tag == "unsorted":
                full_names.append(repo.full_name)

                if repo.full_name.lower() not in self.original_unsorted:
                    print("+ tags_unsorted: " + repo.full_name.lower())


        for full_name in self.original_unsorted:
            if full_name not in self.repos:
                print("- tags_unsorted: " + full_name)

            # star them - unless they have restrict star
        with open(os.path.join(SCRIPT_DIR, 'tags_unsorted.yaml'), 'w') as file:
            yaml.dump(full_names, file)


    def star(self, repo):
        print(emoji.emojize(":star:") + " " + repo.full_name)
        try:
            api.activity.star_repo_for_authenticated_user(owner=repo.owner, repo=repo.name)
        except Exception as e: 
            str = f" Exception Encountered when starring: {repo.full_name} - does the repo exist?"
            print(emoji.emojize(":cross_mark:") + str)
            # print(type(e))
            print(e)
            exit()

    def _star_or_remove_local(self):
        # for repo in self._generate_not_in_stars():
        for [full_name, repo] in self.repos.items():
            if repo.starred == False:
                if repo.tagsym.sub != "unsorted":
                    print("starring repo: " + repo.full_name)
                    repo.starred = True
                    self.star(repo)
                else:
                    print("removing repo: " + repo.full_name)
                    shutil.rmtree(repo.abs)
                    self.repos["full_name"] = None
                

    def _sync_syms(self):
        for [full_name, repo] in self.repos.items():
            repo.symlink()


    def sync(self):
        stars_await = self._download_stars_json()
        print("Retrieving stars from github...")
        self._get_all_repos()
        self._get_download_tags()
        self._get_unsorted()

        stars_await()
        self._get_download_stars()
        # syms are synced and missing stars are symlinked after download
        self._clean_flat_syms()
        self._clean_tag_syms()
        self._sync_syms()
        # self._print_

        # shutdown the pool, cancels scheduled tasks, returns when running tasks complete
        self.pool.shutdown(wait=True, cancel_futures=True)
        self._star_or_remove_local()
        self._write_tags_unsorted()

