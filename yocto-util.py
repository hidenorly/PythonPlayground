
#!/usr/bin/env python3
# coding: utf-8
#   Copyright 2025, 2026 hidenorly
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
from yocto_util_core import YoctoUtil
from GitUtil import GitUtil
from Reporter import Reporter, MarkdownReporter

result = {"Added":[], "Removed":[], "Diffed":[]}

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Yocto util', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-y', '--yocto', action='store', default="poky|openembedded|virtualization", help='Specify target poky|openembedded|virtualization')
    parser.add_argument('-t', '--target', action='store', default="./yocto_components", help='specify git clone root')
    parser.add_argument('-b', '--branch', action='store', default="", help='specify branch. use ... for compare')
    parser.add_argument('-r', '--reset', action='store_true', default=False, help='Remove the target_dir if specified')
    parser.add_argument('-f', '--local', action='store_true', default=False, help='Specify if want to parse .bb under -t folder')
    parser.add_argument('-g', '--gitonly', action='store_true', default=False, help='Dump list of git(s) only')
    parser.add_argument('-l', '--gitlogdelta', action='store_true', default=False, help='Dump list of git log e.g. -b kirkstone...scarthgap -l')
    parser.add_argument('-c', '--componentonly', action='store_true', default=False, help='Dump list of components only')
    parser.add_argument('-p', '--pretty', action='store', default="%h:%as:%s", help='Specify if you want to change the format')
    parser.add_argument('-s', '--grep', action='store', default=None, help='Specify --grep for git log on --gitlogdelta(-l)')
    parser.add_argument('-e', '--grepextract', action='store_true', default=False, help='Specify if you output on grep result. Use with --grep')
    parser.add_argument('-m', '--manifest', action='store_true', default=False, help='Specify if you want to output manifest.xml (exclusive to the others)')

    args = parser.parse_args()

    yocto_targets = args.yocto.split("|")
    yocto_repos = []
    for name in yocto_targets:
        if name in YoctoUtil.REPO_NAME_GITPATH:
            yocto_repos.append( YoctoUtil.REPO_NAME_GITPATH[name] )

    is_print = True
    branches = args.branch.split("...")
    len_branches = len(branches)
    target_base_dirs = args.target.split(",")
    len_targets = len(target_base_dirs)
    target_arguments = [
        (target_base_dirs[0], branches[0])
    ]
    if len_branches==2 or len_targets==2:
        is_print = False
        if len_branches==2 and len_targets==1:
            target_arguments.append( (target_base_dirs[0], branches[1]) )
        elif len_branches==1 and len_targets==2:
            target_arguments.append( (target_base_dirs[1], branches[0]) )
        elif len_branches==2 and len_targets==2: 
            target_arguments.append( (target_base_dirs[1], branches[1]) )

    results = {}
    _branches = []
    for _args in target_arguments:
        clone_root_path = os.path.realpath(os.path.expanduser(_args[0]))
        branch = _args[1]
        if args.local:
            if not branch:
                branch = GitUtil.get_git_name(clone_root_path)
        elif branch:
            clone_root_path = os.path.join(clone_root_path, branch)
        _branches.append(branch)

        results[branch] = {}

        if not args.local:
            YoctoUtil.clone_repos(yocto_repos, clone_root_path, args.reset, branch)
        all_git_info, all_components, all_giturl_components = YoctoUtil.extract_git_src_uris(clone_root_path)
        git_list, git_rev_list, artifact_list = YoctoUtil.get_git_list(all_git_info)
        results[branch]["git_list"] = git_list
        results[branch]["git_rev_list"] = git_rev_list
        results[branch]["artifact_list"] = artifact_list
        results[branch]["components_list"] = all_components
        results[branch]["all_giturl_components"] = all_giturl_components

        if is_print:
            if args.manifest:
                YoctoUtil.generate_repo_manifest(all_git_info)
            elif args.gitonly:
                YoctoUtil.print_git_and_artifactory(git_list, artifact_list, git_rev_list)
            else:
                YoctoUtil.print_all_git_info(all_git_info)

    # before_branch...after_branch analysis
    if len(_branches)==2:
        before = _branches[0]
        after = _branches[1]
        if args.componentonly:
            # component level mode (--componentonly)
            added, removed, diffed, sames = YoctoUtil.analyze_component_delta(results[before]["all_giturl_components"], results[after]["all_giturl_components"])
            for _added in added:
                result["Added"].append({"Added":_added})
            for _removed in removed:
                result["Removed"].append({"Removed":_removed})
            for _ in diffed:
                result["Diffed"].append({"Componet":_[0], before:_[1], after:_[2]})
            reporter = MarkdownReporter()
            reporter.report(result)
            exit(0)

        else:
            # git level mode (--gitonly or --gitlogdelta)
            added, removed, diffed, sames = YoctoUtil.analyze(results, before, after, "git_list")
            diffed = YoctoUtil.enhance_git_analyze_diffed_result(results, before, after, diffed)

        if args.gitlogdelta:
            # git log delta mode
            YoctoUtil.print_git_log_delta(before, after, diffed, args.target, args.pretty, args.grep, args.grepextract, args.reset)
        else:
            # print componennt or git
            YoctoUtil.print_add_removed_delta(before, after, added, removed, diffed)

