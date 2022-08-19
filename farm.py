from globals import home, REPO_DIR, STARFARM_DIR, CONFIG_DIR, REPO_TAG_DIR, REPO_FLAT_DIR, TOKEN
import git, util, os, yaml, multiprocessing, time, shutil, emoji, errno
from subprocess import run
from futil import dump

from ghapi.all import GhApi, pages, paged
api = GhApi(token=TOKEN)
import concurrent, subprocess
from concurrent.futures import ThreadPoolExecutor as Pool




class TagSym():
    def __init__(self, repo, sub):
        self.filename = "|".join([repo.owner.lower(), repo.name.lower()])
        self.repo = repo
        self.sub = sub
        self.target = os.path.join(REPO_TAG_DIR, self.sub, self.filename)


class FlatSym():
    def __init__(self, repo):
        self.filename = "|".join([repo.sub.replace("/", "_"), repo.owner.lower(), repo.name.lower()])
        self.repo = repo
        self.target = os.path.join(REPO_FLAT_DIR, self.filename)


class Repo():
    def __init__(self, abs):
        # in this current version, self.source is replaced by self.abs as there is no need for both now
        if not abs.startswith(STARFARM_DIR):
            self.abs = os.path.join(STARFARM_DIR, abs)
        else:
            self.abs = abs
        gitRepo = git.Repo(self.abs) 
        self.git = gitRepo
        self.full_name = util.url_to_full_name(gitRepo.remotes.origin.url)
        owner_name = self.full_name.split("/")
        self.owner = owner_name[0]
        self.name = owner_name[1]
        self.sub = util.abs_to_sub(self.abs, self.owner, self.name)
        self.starred = False
        self.restrict_star = False
        self.unsorted = False
        
        self.tagsyms = []
        self.flatsym = FlatSym(self)

    def create_tagsym(self, sub):
        self.tagsyms.append(TagSym(self, sub))

    def symlink(self):
        targets = [sym.target for sym in self.tagsyms]

        if self.unsorted:
            targets.append(TagSym(self, "unsorted").target)

        targets.append(self.flatsym.target)

        def do_symlink(source, target):
            if not os.path.lexists(target):
                try:
                    os.symlink(source, target)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        os.makedirs(os.path.dirname(target), mode = 0o777, exist_ok=True)
                        do_symlink(source, target)
                    else:
                        print("failed to create symlink: " + source + " --> " + target)
                        exit()
                else:
                    print("+ " + source + " --> " + target)


        for target in targets:
            do_symlink(self.abs, target)

   
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
        self.manager = multiprocessing.Manager()
        self.pool = Pool()
        self.downloading = []

        if not os.path.lexists(os.path.join(REPO_DIR, "packer")):
            print("packer plugin folder does not exist inside REPO_DIR")
            exit()

        for dir in [REPO_DIR, STARFARM_DIR, REPO_TAG_DIR, REPO_FLAT_DIR, CONFIG_DIR]:
            os.makedirs(os.path.dirname(dir), mode = 0o777, exist_ok=True)



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
                if repo.sub == "packer":
                    repo.create_tagsym(repo.sub)
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
        with open(os.path.join(CONFIG_DIR, path)) as f:
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
                    if tag.endswith("*"):
                        repo.restrict_star = True
                        repo.create_tagsym(tag[:-1])
                    else:
                        repo.create_tagsym(tag)

                    if repo.unsorted:
                        print("- tags_unsorted: " + full_name)
                        repo.unsorted = False
                    else: 
                        sym = TagSym(repo, "unsorted")
                        if os.path.exists(sym.target):
                            print("+ tags_unsorted: " + full_name)
                            print("- Removing symlink: " + sym.target)
                            os.remove(sym.target)
                    



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
                repo.create_tagsym(tag)
                
            if star:
                repo.starred = True

            if not repo.tagsyms:
                repo.unsorted = True
                print("+ tags_unsorted: " + repo.full_name)
            repo.symlink()
            self.downloading.remove(full_name.lower())
        f.add_done_callback(on_complete)

    def _get_unsorted(self):
        for full_name in self._load_yaml_file("tags_unsorted.yaml"):
            if full_name is not None:
                self.repos[full_name.lower()].unsorted = True
                



    def _clean_flat_syms(self):
        for filename in os.listdir(REPO_FLAT_DIR):
            filenameList = filename.split("|")
            full_name = "/".join([filenameList[-2], filenameList[-1]])
            if full_name not in self.repos:
                abs = os.path.join(REPO_FLAT_DIR, filename)
                os.remove(abs)
                print("- Removing symlink: " + abs)

    def _clean_tag_syms(self):
        for abs in util.run_sh(["cd " + REPO_TAG_DIR + " && fd -a --type=l"]): 
            if abs == '':
                continue


            full_name = os.path.basename(abs).replace("|", "/")
            if full_name in self.repos:
                # when removing from tags.yaml, the symlink will exist in tag/sym and it needs to be deleted
                # therefore another check has to be made below
                repo = self.repos[full_name]
                sub = os.path.relpath(os.path.dirname(abs), REPO_TAG_DIR)
                subs = [sym.sub for sym in repo.tagsyms]
                if sub != "unsorted" and not sub in subs:
                    print("- Removing symlink: " + abs)
                    os.remove(abs)
                    print("+ tags_unsorted: " + full_name)
                    repo.unsorted = True       
            else:
                os.remove(abs)
                print("- Removing symlink: " + abs)




    def _write_tags_unsorted(self):
        full_names = []

        for [full_name, repo] in self.repos.items():
            if repo.unsorted: 
                full_names.append(repo.full_name)
            elif not repo.unsorted and not repo.tagsyms:
                full_names.append(repo.full_name)

        with open(os.path.join(CONFIG_DIR, 'tags_unsorted.yaml'), 'w') as file:
            yaml.dump(full_names, file)


    def star(self, repo):
        try:
            api.activity.star_repo_for_authenticated_user(owner=repo.owner, repo=repo.name)
        except Exception as e: 
            str = f" Exception Encountered when starring: {repo.full_name} - does the repo exist?"
            print(emoji.emojize(":cross_mark:") + str)
            print(e)
            exit()
        else:
            print(emoji.emojize(":star:") + " " + repo.full_name)

    def unstar(self, repo):
        # this function is only called from manual
        try:
            api.activity.unstar_repo_for_authenticated_user(owner=repo["owner"], repo=repo["name"])
        except Exception as e: 
            print(e)
            exit()
        else:
            print("unstarred --> " + repo["owner"] + "/" + repo["name"])


    def _star_or_remove_local(self):
        repos_to_remove = []
        for [full_name, repo] in self.repos.items():
             
            if repo.starred == False:
                if repo.unsorted:
                    repos_to_remove.append(full_name)
                else:
                    if not repo.restrict_star:
                        self.star(repo)
                        repo.starred = True

        for full_name in repos_to_remove:
            print("removing repo: " + full_name)
            shutil.rmtree(self.repos[full_name].abs)
            del self.repos[full_name]
            
                

    def _sync_syms(self):
        for [full_name, repo] in self.repos.items():
            repo.symlink()


    def sync(self):
        stars_await = self._download_stars_json()
        print("Retrieving stars from github...")
        self._get_all_repos() 

        self._get_unsorted() 
        self._get_download_tags()

        stars_await()
        self._get_download_stars()
        # star_or_remove_local before syms - as repos unstarred have to be removed from internal repos object, so the symlink functions pick up on the update changes
        # print("star or remove local...")
      
        self._star_or_remove_local()
        # print("cleaning flat syms...")
        self._clean_flat_syms()
        # print("cleaning tag syms...")

        self._clean_tag_syms()
        # print("syncing syms...")
        self._sync_syms()

        # shutdown the pool, returns when running tasks have completed (all repos have finished downloading)
        self.pool.shutdown(wait=True, cancel_futures=True)

        # this doesnt have to wait for all repos to download
        # but as the current implementation writes over the whole tags_unsorted.yaml file once, and there is no incremental write implementation
        # the repos internal dict has to be complete with the current state before writing
        self._write_tags_unsorted()
        util.remove_empty_folders(STARFARM_DIR)
        util.remove_empty_folders(REPO_TAG_DIR)


