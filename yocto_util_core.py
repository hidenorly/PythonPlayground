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


import os
import shutil
import glob
import re
from typing import List, Dict, Any, Tuple
import xml.etree.ElementTree as ET
from xml.dom import minidom

from GitUtil import GitUtil


class YoctoUtil:
    REPO_NAME_GITPATH = {
        "poky" : "git://git.yoctoproject.org/poky",
        "openembedded" : "git://git.openembedded.org/meta-openembedded",
        "virtualization" : "git://git.yoctoproject.org/meta-virtualization",
    }


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
            cloned_path = GitUtil.clone(url, target_dir, branch)
            if not cloned_path:
                GitUtil.pull( os.path.join(target_dir, url) )

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
            if var_name.upper() not in YoctoUtil.EXCLUDES_BB_VARIABLE_KEYS:
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

                    variables = YoctoUtil._parse_variables(content)

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

                    srcrev_defs = YoctoUtil._parse_srcrev_defs(content)

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

    def get_git_log_list(work_root, git_path, before, after, pretty="oneline", grep=None, isReset=False):
        result = ""
        clone_root_path = os.path.join(work_root, GitUtil.get_git_name(git_path))
        YoctoUtil.clone_repos([git_path], work_root, isReset)
        result = GitUtil.log_from_to(clone_root_path, before, after, pretty, grep, True)
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


    def enhance_git_analyze_diffed_result(results, before, after, diffed):
        new_diffed = []
        for _git in diffed:
            _diff = (_git[0], f"{_git[1]}::{results[before]["git_rev_list"][_git[0]]}", f"{_git[2]}::{results[after]["git_rev_list"][_git[0]]}", _git[1], _git[2], results[before]["git_rev_list"][_git[0]], results[after]["git_rev_list"][_git[0]])
            new_diffed.append(_diff)
        return new_diffed


    COMMIT_RE = re.compile(r'^commit\s+([0-9a-f]{40})')

    def filter_git_result_with_grep(result, grep):
        commit_id = None
        for line in str(result).splitlines():
            if not commit_id:
                m_commit = YoctoUtil.COMMIT_RE.match(line)
                if m_commit:
                    commit_id = m_commit.group(1)
            else:
                m = re.search(grep, line, re.IGNORECASE)
                if m:
                    result = f"{commit_id}:{line[m.start():]}"
                    break
        return result


    def print_git_log_delta(before, after, diffed, target, pretty, grep, extract_grep, reset=False):
        for _git in diffed:
            before = _git[3]
            after = _git[4]
            if _git[5]:
                before = _git[5]
            if _git[6]:
                after = _git[6]
            result = YoctoUtil.get_git_log_list(target, _git[0], before, after, (None if extract_grep else pretty), grep, reset)
            if extract_grep:
                result = YoctoUtil.filter_git_result_with_grep(result, grep)
            if result:
                print(f"## {_git[0]} {_git[1]}..{_git[2]}")
                print("")
                print("```")
                print(result)
                print("```")
                print("")


    def print_add_removed_delta(before, after, added=None, removed=None, diffed=None, sames=None):
        if added:
            print(f"Added {before}...{after}")
            for _git in added:
                print(_git)
        if removed:
            print(f"\n\nRemoved {before}...{after}")
            for _git in removed:
                print(_git)
        if diffed:
            print(f"\n\nDelta {before}...{after}")
            for _git in diffed:
                print(f"{_git[0]}: {_git[1]}...{_git[2]}")
        if sames:
            print(f"\n\nSames {before}...{after}")
            for _git in sames:
                print(f"{_git[0]}: {_git[1]}")


    def generate_repo_manifest(all_git_info):
        root = ET.Element("manifest")

        remote = ET.SubElement(root, "remote")
        remote.set("name", "origin")
        remote.set("fetch", ".")

        added_projects = set()

        for recipe in all_git_info:
            recipe_name = recipe["recipe_name"]
            
            for source in recipe["git_repos"]:
                url = source["url"]
                srcrev = source["srcrev"]
                branch = source["branch"]
                tag = source["tag"]
                source_name = source["name"]

                project_name = f"{recipe_name}"
                if source_name:
                    project_name += f"-{source_name}"
                
                revision = srcrev or tag or branch or "master"

                project_key = (url, revision)
                if project_key in added_projects:
                    continue
                
                project = ET.SubElement(root, "project")
                project.set("name", project_name)
                project.set("remote", "origin")
                project.set("revision", revision)
                
                project.set("name", project_name)
                project.set("path", f"{project_name}")
                
                project.set("fetch", url)

                added_projects.add(project_key)

        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
        print(str(pretty_xml_str))
