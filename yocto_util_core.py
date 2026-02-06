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
from typing import List, Dict, Any, Optional, Set, Tuple
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

    RE_VAR_DEFINITION = r'(?m)^([A-Z0-9_:]+)\s*([\.\+\?\:]?=)\s*([\'"])(.*?)\3'
    RE_SHA1 = r'[0-9a-f]{40}'

    @staticmethod
    def _preprocess_content(content: str) -> str:
        content = re.sub(r'\\\s*\n\s*', ' ', content)
        content = re.sub(r'(?m)^\s*#.*$', '', content)
        return content

    def _clean_srcrev(val: str) -> str:
        val = val.strip()
        # check sha1
        if re.fullmatch(YoctoUtil.RE_SHA1, val):
            return val
        # check sha1 in the quote
        sha_matches = re.findall(r'[\'"](' + YoctoUtil.RE_SHA1 + r')[\'"]', val)
        if sha_matches:
            return sha_matches[0]
        # check AUTOREV
        if "${AUTOREV}" in val or "AUTOREV" in val:
            return "AUTOREV"
        return val

    @staticmethod
    def _parse_content_to_dict(content: str, data: Dict[str, Any]):
        # flatten \n to " "
        processed_content = YoctoUtil._preprocess_content(content)

        var_matches = re.findall(YoctoUtil.RE_VAR_DEFINITION, processed_content, re.IGNORECASE | re.DOTALL)

        for var_name, op, _, val in var_matches:
            val = val.strip()

            # SRC_URI
            if "SRC_URI" in var_name:
                if ":remove" in var_name or "_remove" in var_name:
                    for item in val.split():
                        data['src_uri_removals'].add(item)
                elif ":append" in var_name or "_append" in var_name or "+=" in op:
                    data['src_uri'] += " " + val
                elif ":prepend" in var_name or "_prepend" in var_name or "=+" in op:
                    data['src_uri'] = val + " " + data['src_uri']
                else:
                    data['src_uri'] = val

            # SRCREV
            elif "SRCREV" in var_name:
                name_key = var_name.replace("SRCREV", "").strip('_').strip(':').upper()
                if not name_key or name_key == "FORCEVARIABLE": name_key = "DEFAULT"
                data['srcrev_defs'][name_key] = val #YoctoUtil._clean_srcrev(val)

            # other variables
            elif ":" not in var_name and var_name.upper() not in YoctoUtil.EXCLUDES_BB_VARIABLE_KEYS:
                data['vars'][var_name] = val

    @staticmethod
    def extract_git_src_uris(yocto_layers_path="yocto_components"):
        all_git_info: List[Dict[str, Any]] = []
        all_components = {}

        recipe_groups = {} # { bpn: { 'base': path, 'appends': [paths], 'pv': val } }

        for filepath in glob.glob(os.path.join(yocto_layers_path, '**', '*.[b][b]*'), recursive=True):
            filename = os.path.basename(filepath)
            if filename.endswith('.bb'):
                match = re.match(r'(.+?)_([v|r]?\d.*)\.bb$', filename)
                bpn = match.group(1) if match else filename.replace('.bb', '')
                pv = match.group(2) if match else ""
                if bpn not in recipe_groups: recipe_groups[bpn] = {'base': None, 'appends': [], 'pv': pv}
                recipe_groups[bpn]['base'] = filepath
            elif filename.endswith('.bbappend'):
                bpn = filename.split('_')[0].replace('.bbappend', '')
                if bpn not in recipe_groups: recipe_groups[bpn] = {'base': None, 'appends': [], 'pv': ""}
                recipe_groups[bpn]['appends'].append(filepath)

        for bpn, files in recipe_groups.items():
            #if not files['base']: continue # ignore if no base recipe

            recipe_data = {
                'src_uri': "",
                'src_uri_removals': set(),
                'srcrev_defs': {},
                'vars': {'BPN': bpn, 'PV': files['pv'], 'BP': bpn},
                'recipe_file': files['base']
            }

            try:
                # parse .bb
                if files['base']:
                    with open(files['base'], 'r', encoding='utf-8', errors='ignore') as f:
                        YoctoUtil._parse_content_to_dict(f.read(), recipe_data)

                # parse .bbappend
                if files['appends']:
                    for append_path in sorted(files['appends']):
                        with open(append_path, 'r', encoding='utf-8', errors='ignore') as f:
                            YoctoUtil._parse_content_to_dict(f.read(), recipe_data)

                for _ in range(3):
                    for target_key in recipe_data['vars'].keys():
                        val = recipe_data['vars'][target_key]
                        for v_name, v_val in recipe_data['vars'].items():
                            if target_key == v_name: continue
                            val = val.replace(f"${{{v_name}}}", v_val).replace(f"${v_name}", v_val)
                        recipe_data['vars'][target_key] = val

                for name_key in recipe_data['srcrev_defs'].keys():
                    raw_val = recipe_data['srcrev_defs'][name_key]
                    for v_name, v_val in recipe_data['vars'].items():
                        raw_val = raw_val.replace(f"${{{v_name}}}", v_val).replace(f"${v_name}", v_val)
                    recipe_data['srcrev_defs'][name_key] = YoctoUtil._clean_srcrev(raw_val)

                # ensure SRC_URI
                # --- replace variables
                resolved_uri = recipe_data['src_uri']
                for v_name, v_val in recipe_data['vars'].items():
                    resolved_uri = resolved_uri.replace(f"${{{v_name}}}", v_val).replace(f"${v_name}", v_val)

                # --- apply remove
                uri_items = resolved_uri.split()
                removals = recipe_data['src_uri_removals']
                filtered_items = [item for item in uri_items if item not in removals]
                resolved_uri = " ".join(filtered_items)

                # extract Git info.
                _git_repos_raw = []
                _keys_set = set()

                for part in filtered_items:
                    if part.startswith(('git://', 'https://', 'http://', 'ssh://')) and \
                       ('.git' in part or 'git.yoctoproject.org' in part or 'github' in part):

                        uri_parts = part.split(';')
                        base_url = uri_parts[0]
                        params = {p.split('=')[0]: p.split('=')[1] for p in uri_parts[1:] if '=' in p}

                        name = params.get('name')
                        srcrev_key = name.upper() if name else "DEFAULT"
                        srcrev_val = recipe_data['srcrev_defs'].get(srcrev_key) or recipe_data['srcrev_defs'].get("DEFAULT")

                        _key = (base_url, name, params.get('branch'), params.get('tag'), srcrev_val)
                        if _key not in _keys_set:
                            _keys_set.add(_key)
                            _git_repos_raw.append(_key)

                _git_repos_raw.sort(key=lambda x: (x[1] or "", x[0]))

                git_repos = []
                for url, name, branch, tag, srcrev in _git_repos_raw:
                    effective_rev = srcrev
                    if srcrev == "AUTOREV" or not srcrev:
                        effective_rev = branch or tag or "master"
                    git_repos.append({
                        "name": name,
                        "url": url,
                        "branch": branch,
                        "tag": tag,
                        "srcrev": effective_rev
                    })

                if git_repos:
                    all_git_info.append({
                        "recipe_file": files['base'],
                        "recipe_name": os.path.basename(files['base']).replace(".bb", ""),
                        "git_repos": git_repos,
                        "srcrev": recipe_data['srcrev_defs'].get("DEFAULT")
                    })
                    all_components[bpn] = files['pv']

            except Exception as e:
                print(f"Error processing {bpn}: {e}")

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


    def print_git_and_artifactory(git_list, artifact_list, git_rev_list):
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
            for _git in sorted(added):
                print(_git)
        if removed:
            print(f"\n\nRemoved {before}...{after}")
            for _git in sorted(removed):
                print(_git)
        if diffed:
            print(f"\n\nDelta {before}...{after}")
            for _git in sorted(diffed):
                print(f"{_git[0]}: {_git[1]}...{_git[2]}")
        if sames:
            print(f"\n\nSames {before}...{after}")
            for _git in sorted(sames):
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
                if not url.endswith(".git") and not url.startswith("git://"):
                    continue
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
