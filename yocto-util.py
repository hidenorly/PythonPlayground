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
import glob
import re
from typing import List, Dict, Any, Tuple

yocto_repos = [
    #"git://git.yoctoproject.org/poky",
    "git://git.openembedded.org/meta-openembedded",
    # "git://git.yoctoproject.org/meta-virtualization",
]

def clone_repos(repos, target_dir="yocto_components", branch=None):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for url in repos:
        repo_name = url.split('/')[-1]
        print(f"Cloning {repo_name} from {url}...")
        # TODO : branch
        exec_git_clone_cmd = ["git", "clone", url]
        if branch:
            exec_git_clone_cmd.append("-b")
            exec_git_clone_cmd.append(branch)

        try:
            subprocess.run(
                exec_git_clone_cmd,
                cwd=target_dir,
                check=True
            )
            print(f"Successfully cloned {repo_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error cloning {repo_name}: {e}")
            try:
                #subprocess.run(
                #    ["git", "reset", "HEAD", "--hard"],
                #    cwd=target_dir,
                #    check=True
                #)
                subprocess.run(
                    ["git", "pull"],
                    cwd=target_dir,
                    check=True
                )
                print(f"Successfully cloned {repo_name}")
            except:
                pass

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

    return all_git_info


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Yocto util', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-t', '--target', action='store', default="./yocto_components", help='specify git clone root')
    parser.add_argument('-b', '--branch', action='store', default=None, help='specify branch')
    args = parser.parse_args()

    clone_repos(yocto_repos, args.target, args.branch)
    all_git_info = extract_git_src_uris()
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
