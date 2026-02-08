#!/usr/bin/env python3
# coding: utf-8
#   Copyright 2026 hidenorly
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
import os
import re
from yocto_util_core import YoctoUtil
from GitUtil import GitUtil
from ModifiedGitApiAnalysis import ModifiedGitChecker
from ApiChecker import CAbiUtil


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Yocto util', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-y', '--yocto', action='store', default="poky|openembedded|virtualization", help='Specify target poky|openembedded|virtualization')
    parser.add_argument('-t', '--temp', action='store', default="./yocto_components", help='specify git clone root')
    parser.add_argument('-b', '--branch', action='store', default="", help='specify branch. use ... for compare')
    parser.add_argument('-r', '--reset', action='store_true', default=False, help='Remove the target_dir if specified')
    parser.add_argument('-i', '--interested', action='store', default="h|hxx|hpp|proto|capnp|dart", help='specify interested file extensions (separator:|)')
    parser.add_argument('-p', '--greppath', action='store', default="(include|public|inc|api)", help='specify interested file path (grep expression)')
    parser.add_argument('-e', '--excludepath', action='store', default="private", help='specify exclude file path (grep expression)')
    parser.add_argument('-s', '--stat', action='store_true', default=False, help='Dump stat if specified')

    args = parser.parse_args()

    yocto_targets = args.yocto.split("|")
    yocto_repos = []
    for name in yocto_targets:
        if name in YoctoUtil.REPO_NAME_GITPATH:
            yocto_repos.append( YoctoUtil.REPO_NAME_GITPATH[name] )

    branches = args.branch.split("...")
    if len(branches)!=2:
        print("You need to specify branch e.g -b kirkstone..scarthgap")

    is_reset = args.reset
    is_only_stat = args.stat
    temp_path = os.path.abspath(os.path.expanduser(args.temp))
    temp_diff_path = os.path.join(temp_path, "srcs")

    file_extensions = []
    interests = args.interested.split("|")
    for ext in interests:
        file_extensions.append(f".{ext}")

    results = {}
    # clone & parse recipes
    for branch in branches:
        results[branch] = {}
        clone_root_path = os.path.join(temp_path, branch)
        YoctoUtil.clone_repos(yocto_repos, clone_root_path, is_reset, branch)
        all_git_info, all_components, _ = YoctoUtil.extract_git_src_uris(clone_root_path)
        git_list, git_rev_list, artifact_list = YoctoUtil.get_git_list(all_git_info)
        results[branch]["git_list"] = git_list
        results[branch]["git_rev_list"] = git_rev_list
        results[branch]["artifact_list"] = artifact_list
        results[branch]["components_list"] = all_components

    # before_branch...after_branch analysis
    before = branches[0]
    after = branches[1]

    added, removed, diffed, sames = YoctoUtil.analyze(results, before, after, "git_list")
    diffed = YoctoUtil.enhance_git_analyze_diffed_result(results, before, after, diffed)

    for a_diff in diffed:
        git_uri = a_diff[0]
        git_path = GitUtil.clone(git_uri, temp_path)
        if git_path:
            _before = a_diff[5]
            _after = a_diff[6]
            is_separator_output = False
            changes = ModifiedGitChecker.extract_git_old_new( git_path, temp_diff_path, [_before, _after], 
                file_extensions, args.greppath, args.excludepath )

            cnt_removed = 0
            cnt_changed = 0
            cnt_incompatible_files = 0
            incompatible_files = []

            for file, a_changes in changes.items():
                removed, changed, added = ModifiedGitChecker.check_abi(file, a_changes)

                cnt_removed += len(removed)
                cnt_changed += len(changed)
                if removed or changed:
                    cnt_incompatible_files += 1
                    incompatible_files.append(file)

                if not is_only_stat:
                    old_path = a_changes[0]
                    new_path = a_changes[1]

                    if not is_separator_output:
                        is_separator_output = True
                        print(f"\n# {git_uri} {a_diff[1]}..{a_diff[2]}\n")

                    if removed or changed:
                        # incompatible case
                        CAbiUtil.dump_results(removed, "Function removed", old_path, new_path)
                        CAbiUtil.dump_results(changed, "Signature changed", old_path, new_path)
                    else:
                        # compatible case
                        #CAbiUtil.dump_results(added, "Function added", old_path, new_path)
                        print(f"No incompatible changes...{file}")

            if cnt_incompatible_files:
                if not is_separator_output:
                    is_separator_output = True
                    print(f"\n# {git_uri} {a_diff[1]}..{a_diff[2]}")
                print(f"\nIncompatible files:{cnt_incompatible_files}, removed:{cnt_removed}, changed:{cnt_changed}")
                print("\n```")
                print("\n".join(incompatible_files))
                print("```")


