#!/usr/bin/env python3
# coding: utf-8
#   Copyright 2025 hidenorly
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import argparse
import subprocess
import os
import shutil
import glob
import re
from typing import List, Dict, Any, Tuple

yocto_repos = [
    #"git://git.yoctoproject.org/poky",
    "git://git.openembedded.org/meta-openembedded",
    # "git://git.yoctoproject.org/meta-virtualization",
]

def exec_cmd_with_result(exec_cmd, exec_path):
    if not os.path.exists(exec_path):
        os.makedirs(exec_path)

    result = subprocess.run(
        exec_cmd,
        cwd=exec_path,
        check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    return str(result.stdout)

def clone_repos(repos, target_dir="yocto_components", isReset=False, branch=None):
    result = ""
    if os.path.exists(target_dir) and isReset:
        try:
            #print(f"rm -rf {target_dir}")
            shutil.rmtree(target_dir)
        except:
            pass
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for url in repos:
        repo_name = url.split('/')[-1]
        #print(f"Cloning {repo_name} from {url}...")

        exec_git_clone_cmd = ["git", "clone", url]
        if branch:
            exec_git_clone_cmd.append("-b")
            exec_git_clone_cmd.append(branch)

        try:
            result += exec_cmd_with_result(exec_git_clone_cmd, target_dir)
            #print(f"Successfully cloned {repo_name}")
        except subprocess.CalledProcessError as e:
            #print(f"Error cloning {repo_name}: {e}")
            try:
                #TODO: branch
                exec_cmd = ["git", "pull"]
                result += exec_cmd_with_result(exec_cmd, target_dir)
                #print(f"Successfully cloned {repo_name}")
            except:
                pass
    return result

EXCLUDES_BB_VARIABLE_KEYS = [
    "SUMMARY",
    "DESCRIPTION",
    "HOMEPAGE",
    "LICENSE",
    "LIC_FILES_CHKSUM",
    "SECTION",
    "SRC_URI",
    "SRCREV",
    "PACKAGES",
    "DEPENDS",
    "FILES"
]

def _parse_variables(content: str) -> Dict[str, str]:
    variables = {}
    
    var_matches = re.findall(
        r'(?m)^([A-Z_]+)\s*=\s*([\'"])(.*?)\2$', 
        content, 
        re.IGNORECASE
    )
    
    for var_name, _, var_value in var_matches:
        if var_name.upper() not in EXCLUDES_BB_VARIABLE_KEYS:
            variables[var_name] = var_value.strip()

    return variables


def _parse_srcrev_defs(content: str):
    srcrev_defs = {}
    srcrev_matches = re.findall(
        r'(?m)^(\s*SRCREV(?:_[A-Z0-9_-]+)?)\s*=\s*([\'"])(.*?)\2$', 
        content, 
        re.IGNORECASE
    )
    
    for srcrev_var, _, sha_value in srcrev_matches:
        name_key = srcrev_var.strip().upper().replace("SRCREV", "").strip('_')
        
        if not name_key:
            name_key = "default"
            
        srcrev_defs[name_key] = sha_value.strip()

    return srcrev_defs

def extract_git_src_uris(yocto_layers_path="yocto_components"):
    all_git_info: List[Dict[str, Any]] = []
    all_components = {}

    for filepath in glob.glob(os.path.join(yocto_layers_path, '**', '*.bb'), recursive=True):
        filename = os.path.basename(filepath)
        recipe_name = os.path.basename(filepath).replace(".bb", "")
        #print(f"...{filepath}")
        recipe_info = {
            "recipe_file": filepath,
            "recipe_name": recipe_name,
            "git_repos": []
        }
        _git_repos_set = set()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

                variables = _parse_variables(content)

                match = re.match(r'(.+?)_([v|r]?\d.*)\.bb$', filename)
                guessed_bpn = match.group(1) if match else recipe_name
                if guessed_bpn:
                    variables['BPN'] = guessed_bpn
                    variables['BP'] = guessed_bpn
                guessed_pv = match.group(2) if match else None
                if guessed_pv:
                    variables['PV'] = guessed_pv
                if guessed_pv or not guessed_bpn in all_components:
                    all_components[guessed_bpn] = guessed_pv

                srcrev_defs = _parse_srcrev_defs(content)

                srcrev_match = re.search(
                    r'(?m)^SRCREV\s*=\s*([\'"])(.*?)\1', 
                    content, 
                    re.IGNORECASE
                )
                recipe_info["srcrev"] = srcrev_match.group(2).strip() if srcrev_match else None

                src_uri_lines = re.findall(
                    r'(?m)^SRC_URI\s*(\+\?*)*=\s*([\'"])(.*?)\2$', 
                    content, 
                    re.IGNORECASE | re.DOTALL
                )

                for _, _, uri_string in src_uri_lines:
                    resolved_uri_string = uri_string
                    for var_name, var_value in variables.items():
                        resolved_uri_string = resolved_uri_string.replace(f"${{{var_name}}}", var_value)
                    uris = resolved_uri_string.split()
                    
                    for uri in uris:
                        uri = uri.strip()
                        if uri.startswith(('git://', 'ssh://', 'http://', 'https://')):
                            parts = uri.split(';')
                            base_uri = parts[0].strip()
                            if '.git' in base_uri or 'git.yoctoproject.org' in base_uri:
                                branch = None
                                name = None
                                tag = None
                                for part in parts[1:]:
                                    part = part.strip()
                                    if part.lower().startswith('name='):
                                        name = part.split('=', 1)[1].strip()
                                    elif part.lower().startswith('branch='):
                                        branch = part.split('=', 1)[1].strip()
                                    elif part.lower().startswith('tag='):
                                        tag = part.split('=', 1)[1].strip()

                                _git_repos_set.add( (base_uri, name, branch, tag) )

                if _git_repos_set:
                    _git_repos = []
                    for base_uri, name, branch, tag in _git_repos_set:
                        srcrev_key = name.upper() if name else "default"
                        resolved_srcrev = srcrev_defs.get(srcrev_key)
                        _git_repos.append({
                                "name": name,
                                "url": base_uri,
                                "branch": branch,
                                "tag": tag,
                                "srcrev" : resolved_srcrev
                        })
                    recipe_info["git_repos"] = _git_repos

                    all_git_info.append(recipe_info)
                        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    return all_git_info, all_components


def get_git_list(all_git_info):
    git_list = {}
    artifact_list = {}
    git_rev_list = {}

    for git_info in all_git_info:
        for key,value in git_info.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if "url" in item and "branch" in item:
                            url = item["url"]
                            branch = item["branch"]
                            srcrev = None
                            if "srcrev" in item:
                                srcrev = item["srcrev"]
                            if url.endswith(".git") or url.startswith("git://"):
                                git_list[url] = branch
                                git_rev_list[url] = srcrev
                            else:
                                artifact_list[url] = branch

    git_list = dict(sorted(git_list.items(), key=lambda x: (x[0])))
    artifact_list = dict(sorted(artifact_list.items(), key=lambda x: (x[0])))

    return git_list, git_rev_list, artifact_list


def analyze(results, before, after, target_key="git_list"):
    before_gits = set(results[before][target_key].keys()) 
    after_gits = set(results[after][target_key].keys()) 

    added = sorted(list( after_gits - before_gits ))
    removed = sorted(list( before_gits - after_gits ))
    anded = before_gits & after_gits

    diffed = []
    sames = []
    for _git in anded:
        _before = str(results[before][target_key][_git]).strip()
        _after = str(results[after][target_key][_git]).strip()
        if _before == _after:
            sames.append( (_git, _before) )
        else:
            diffed.append( (_git, _before, _after) )

    return added, removed, diffed, sames

def get_component_name_from_git_path(git_path):
    result = str(git_path).split(".git")[0].strip()
    return result.split("/")[-1]


def get_git_log_list(work_root, git_path, before, after, pretty="oneline", isReset=False):
    result = ""
    clone_root_path = os.path.join(work_root, get_component_name_from_git_path(git_path))
    clone_repos([git_path], work_root, isReset)
    exec_cmd_git_log = ["git", "log", f"--pretty={pretty}", f"{before}..{after}", "--no-merges"]
    try:
        result = exec_cmd_with_result(exec_cmd_git_log, clone_root_path)
    except:
        pass
    return str(result)


def print_git_and_artifactory(git_list, artifact_list):
    for git, branch in git_list.items():
        srcrev = git_rev_list[git]
        if branch:
            print(f"git clone {git} -b {branch}; git checkout {srcrev}")
        else:
            print(f"git clone {git}; git checkout {srcrev}")
    for git, branch in artifact_list.items():
        print(f"wget {git} #{branch}")

def print_all_git_info(all_git_info):
    for git_info in all_git_info:
        for key,value in git_info.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for _k, _v in item.items():
                            print(f"\t{_k}:\t{_v}")
            else:
                print(f"{key}:\t{value}")
        print("")


def print_git_log_delta(before, after, diffed, target, pretty, reset=False):
    for _git in diffed:
        before = _git[3]
        after = _git[4]
        if _git[5]:
            before = _git[5]
        if _git[6]:
            after = _git[6]
        result = get_git_log_list(target, _git[0], before, after, pretty, reset)
        print(f"## {_git[0]} {_git[1]}..{_git[2]}")
        print("")
        print("```")
        print(result)
        print("```")
        print("")


def print_add_removed_delta(before, after, added, removed, diffed):
    print(f"Added {before}...{after}")
    for _git in added:
        print(_git)
    print(f"\n\nRemoved {before}...{after}")
    for _git in removed:
        print(_git)
    print(f"\n\nDelta {before}...{after}")
    for _git in diffed:
        print(f"{_git[0]}: {_git[1]}...{_git[2]}")
    print(f"\n\nSames {before}...{after}")
    for _git in sames:
        print(f"{_git[0]}: {_git[1]}")

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Yocto util', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--target', action='store', default="./yocto_components", help='specify git clone root')
    parser.add_argument('-b', '--branch', action='store', default="", help='specify branch. use ... for compare')
    parser.add_argument('-r', '--reset', action='store_true', default=False, help='Remove the target_dir if specified')
    parser.add_argument('-g', '--gitonly', action='store_true', default=False, help='Dump list of git(s) only')
    parser.add_argument('-l', '--gitlogdelta', action='store_true', default=False, help='Dump list of git log e.g. -b kirkstone...scarthgap -l')
    parser.add_argument('-c', '--componentonly', action='store_true', default=False, help='Dump list of components only')
    parser.add_argument('-p', '--pretty', action='store', default="%h:%as:%s", help='Specify if you want to change the format')

    args = parser.parse_args()

    is_print = True
    branches = args.branch.split("...")
    if len(branches)==2:
        is_print = False
    results = {}
    for branch in branches:
        results[branch] = {}
        clone_root_path = args.target
        if branch:
            clone_root_path = os.path.join(clone_root_path, branch)
        clone_repos(yocto_repos, clone_root_path, args.reset, branch)
        all_git_info, all_components = extract_git_src_uris(clone_root_path)
        git_list, git_rev_list, artifact_list = get_git_list(all_git_info)
        results[branch]["git_list"] = git_list
        results[branch]["git_rev_list"] = git_rev_list
        results[branch]["artifact_list"] = artifact_list
        results[branch]["components_list"] = all_components

        if is_print:
            if args.gitonly:
                print_git_and_artifactory(git_list, artifact_list)
            else:
                print_all_git_info(all_git_info)

    # before_branch...after_branch analysis
    if len(branches)==2:
        before = branches[0]
        after = branches[1]
        if args.componentonly:
            # component level mode (--componentonly)
            added, removed, diffed, sames = analyze(results, before, after, "components_list")
        else:
            # git level mode (--gitonly or --gitlogdelta)
            added, removed, diffed, sames = analyze(results, before, after, "git_list")
            new_diffed = []
            for _git in diffed:
                _diff = (_git[0], f"{_git[1]}::{results[before]["git_rev_list"][_git[0]]}", f"{_git[2]}::{results[after]["git_rev_list"][_git[0]]}", _git[1], _git[2], results[before]["git_rev_list"][_git[0]], results[after]["git_rev_list"][_git[0]])
                new_diffed.append(_diff)
            diffed = new_diffed

        if args.gitlogdelta:
            # git log delta mode
            print_git_log_delta(before, after, diffed, args.target, args.pretty, args.reset)
        else:
            # print componennt or git
            print_add_removed_delta(before, after, added, removed, diffed)

