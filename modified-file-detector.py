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

def changed_files(git_path, from_shaish, to_shaish, file_extensions):
	try:
		cmd = ["git", "diff", "--name-only", f"{from_shaish}..{to_shaish}"]
		out = subprocess.check_output(cmd, cwd=git_path, text=True)
		return [
			f for f in out.splitlines()
			if f.endswith(tuple(file_extensions))
	    ]
	except:
		return []

if __name__=="__main__":
	parser = argparse.ArgumentParser(description='modified file detectpr', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-t', '--target', action='store', default=".", help='specify git directory')
	parser.add_argument('-b', '--branch', action='store', default="", help='specify branch. use .. for compare')
	parser.add_argument('-i', '--interested', action='store', default="h|hxx|hpp|proto|capnp|dart", help='specify interested file extensions (separator:|)')

	args = parser.parse_args()

	branches = args.branch.split("..")
	interests = args.interested.split("|")
	file_extensions = []
	for ext in interests:
		file_extensions.append(f".{ext}")
	if len(branches)==2:
		changed_files = changed_files(args.target, branches[0], branches[1], file_extensions)
		for file in changed_files:
			print(file)
