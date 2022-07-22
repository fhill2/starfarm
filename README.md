# StarFarm

Dependencies
```bash
pip install emoji ghapi pygithub
```
Github Stars <-> REPO_DIR
Github Stars (read only)-> tags_unsorted.yaml
tags.yaml -> REPO_SYM_DIR
tags_unsorted.yaml (read only) -> REPO_SYM_DIR


To use:
- install requirements
- add your github PAT token and paste into globals.py - or use pass
- edit/confirm locations for REPO_DIR, REPO_SYM_DIR, PLUGIN_DIR in globals.py
- create tags.yaml in project root


### Example tags.yaml
```yaml
shell:
- jarun/nnn
- kovidgoyal/kitty

ansible_vagrant:
- xcad2k/boilerplates
- geerlingguy/ansible-for-devops

i3:
- i3/i3
- JonnyHaystack/i3-resurrect
- eliep/i3-layouts

python_hypothesis*:
- cdown/aur
```
- append `*` to tag name and the script won't star the repo
any starred repos that are nvim plugins (PLUGIN_DIR) won't be cloned (I don't need 2 instances of the same repo on my machine)
script won't ever unstar repos


### Workflow
when starring a repo online
- newly starred repo is cloned into REPO_DIR
- repo is added to tags_unsorted.yaml
- symlink is created in REPO_SYM_DIR (unsorted tag automatically applied)

when unstarring a repo online:
- unstarred repo is removed from REPO_DIR
- repo is removed from tags_unsorted.yaml if it exists
- (note): if the repo is in tags.yaml, it also has to be deleted to unstar the repo, otherwise it will be cloned on next run.

add repos to tags.yaml:
- newly added repo is cloned into REPO_DIR
- symlink is created in REPO_SYM_DIR in the tag folder

move repos from tags_unsorted.yaml to tags.yaml to categorize unsorted repos:
- symlink is removed from REPO_SYM_DIR unsorted tag folder
- symlink is created in REPO_SYM_DIR tag folder
- (note): if you add new repos to tags_unsorted.yaml they will be deleted (file is read-only)


