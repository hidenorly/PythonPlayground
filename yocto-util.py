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


import subprocess
import os
import glob
import re

yocto_repos = [
    #"git://git.yoctoproject.org/poky",
    "git://git.openembedded.org/meta-openembedded",
    # "git://git.yoctoproject.org/meta-virtualization",
]

def clone_repos(repos, target_dir="yocto_components"):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for url in repos:
        repo_name = url.split('/')[-1]
        print(f"Cloning {repo_name} from {url}...")
        # TODO : branch
        try:
            subprocess.run(
                ["git", "clone", url],
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


def extract_git_src_uris(yocto_layers_path="yocto_components"):
    all_git_info: List[Dict[str, Any]] = []

    for filepath in glob.glob(os.path.join(yocto_layers_path, '**', '*.bb'), recursive=True):
        recipe_name = os.path.basename(filepath).replace(".bb", "")
        print(f"...{filepath}")
        recipe_info = {
            "recipe_file": filepath,
            "recipe_name": recipe_name,
            "git_repos": []
        }
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
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
                    uris = uri_string.split()
                    
                    for uri in uris:
                        uri = uri.strip()
                        if uri.startswith(('git://', 'ssh://', 'http://', 'https://')):
                            parts = uri.split(';')
                            base_uri = parts[0].strip()
                            if '.git' in base_uri or 'git.yoctoproject.org' in base_uri:
                                branch = None
                                for part in parts[1:]:
                                    if part.lower().startswith('branch='):
                                        branch = part.split('=', 1)[1].strip()
                                        break

                                recipe_info["git_repos"].append({
                                    "url": base_uri,
                                    "branch": branch
                                })

                if recipe_info["git_repos"]:
                    all_git_info.append(recipe_info)
                        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

    return all_git_info


if __name__=="__main__":
    clone_repos(yocto_repos)
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
