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


import os
import argparse
from ModifiedGitApiAnalysis import ModifiedGitChecker


if __name__=="__main__":
	parser = argparse.ArgumentParser(description='modified file detectpr', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-g', '--git', action='store', default=".", help='specify git directory or https://github.com/id/repo')
	parser.add_argument('-t', '--temp', action='store', default="~/tmp", help='specify temp directory')
	parser.add_argument('-b', '--branch', action='store', default="", help='specify branch. use .. for compare')
	parser.add_argument('-i', '--interested', action='store', default="h|hxx|hpp|proto|capnp|dart", help='specify interested file extensions (separator:|)')

	args = parser.parse_args()

	tmp_path = os.path.abspath(os.path.expanduser(args.temp))
	branches = args.branch.split("..")
	interests = args.interested.split("|")

	git_path = ModifiedGitChecker.ensure_git_clone(args.git, os.path.join(tmp_path, "srcs"))

	file_extensions = []
	for ext in interests:
		file_extensions.append(f".{ext}")

	changes = ModifiedGitChecker.extract_git_old_new( git_path, tmp_path, branches, file_extensions )
	for file, a_changes in changes.items():
		ModifiedGitChecker.check_abi_and_dump(file, a_changes)
