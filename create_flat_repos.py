#!/usr/bin/python
import subprocess
import os
from get import mkdir, get_all_repos, get_flat_repos, filter_by_fullname
from globals import REPO_DIR, REPO_FLAT_DIR

all_repos = get_all_repos()
flat_repos = get_flat_repos()



# symlink new repos into REPO_FLAT_DIR
print("for all repos not in flat syms: -- create syms.. ")
all_noflat = filter_by_fullname(all_repos, flat_repos)



print("for flat syms not in all repos - remove syms...")
flat_noall = filter_by_fullname(flat_repos, all_repos)
## REMOVE SYMS.. MAKE SUR
for repo in flat_noall:
    abs = os.path.join(REPO_FLAT_DIR, repo["filename"])
    print("Removing: " + abs)
    os.remove(abs)


