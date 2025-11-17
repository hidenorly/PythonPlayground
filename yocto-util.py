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
                subprocess.run(
                    ["git", "reset", "HEAD", "--hard"],
                    cwd=target_dir,
                    check=True
                )
                subprocess.run(
                    ["git", "pull"],
                    cwd=target_dir,
                    check=True
                )
                print(f"Successfully cloned {repo_name}")
            except:
                pass


if __name__=="__main__":
    clone_repos(yocto_repos)