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
from GitUtil import GitUtil

class FileUtil:
	@staticmethod
	def write_file(path, lines):
		with open(path, 'w', encoding='utf-8', errors='ignore') as f:
			f.writelines(lines)


def extract_git_old_new(git_path, temp_path, branches, interests):
	if len(branches)!=2:
		if not branches[0]:
			branches[0]="HEAD"
		branches = [GitUtil.get_tail(git_path), branches[0]]
	changed_files = GitUtil.changed_files(git_path, branches[0], branches[1], file_extensions)

	changed = {}

	for file in changed_files:
		contents = []
		contents.append( GitUtil.show(git_path, branches[0], file) )
		contents.append( GitUtil.show(git_path, branches[1], file) )
		if contents[0] and contents[1]:
			git_name = GitUtil.get_git_name(git_path)
			temp_out_path = os.path.join(tmp_path, git_name)
			for branch, content in zip(branches, contents):
				temp_out_file_dir = os.path.join(temp_out_path, branch)
				if not os.path.exists(temp_out_file_dir):
					os.makedirs(temp_out_file_dir)
				file_out_path = os.path.join(temp_out_file_dir, file)
				FileUtil.write_file( file_out_path , content )
				if not file in changed:
					changed[file] = []
				changed[file].append( file_out_path )

	return changed



if __name__=="__main__":
	parser = argparse.ArgumentParser(description='modified file detectpr', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('-g', '--git', action='store', default=".", help='specify git directory')
	parser.add_argument('-t', '--temp', action='store', default="~/tmp", help='specify temp directory')
	parser.add_argument('-b', '--branch', action='store', default="", help='specify branch. use .. for compare')
	parser.add_argument('-i', '--interested', action='store', default="h|hxx|hpp|proto|capnp|dart", help='specify interested file extensions (separator:|)')

	args = parser.parse_args()

	git_path = os.path.abspath(os.path.expanduser(args.git))
	tmp_path = os.path.abspath(os.path.expanduser(args.temp))
	branches = args.branch.split("..")
	interests = args.interested.split("|")

	file_extensions = []
	for ext in interests:
		file_extensions.append(f".{ext}")


	changes = extract_git_old_new( git_path, tmp_path, branches, file_extensions )
	for file, a_changes in changes.items():
		for change in a_changes:
			print(f"{file}:{change}")
		print("")

