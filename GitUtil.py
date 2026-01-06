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
import subprocess
from ExecUtil import ExecUtil

class GitUtil:
	@staticmethod
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

	@staticmethod
	def get_tail(git_path):
		cmd = ["git", "log", "--pretty=%H"]
		out = subprocess.check_output(cmd, cwd=git_path, text=True)
		return out.splitlines()[-1]

	@staticmethod
	def is_git_directory(git_path):
		return os.path.exists(os.path.join(git_path, ".git"))

	@staticmethod
	def show(git_path, sha1, file=None):
		results = []
		try:
			exec_cmd = [
				"git",
				"show"
			]
			if file:
				exec_cmd.append(f"{sha1}:{file}")
			else:
				exec_cmd.append(sha1)
			results = ExecUtil.exec_cmd_with_result(exec_cmd, git_path)
		except:
			pass
		return results

	@staticmethod
	def get_git_name(git_path):
		git_name = ""
		if GitUtil.is_git_directory(git_path):
			abs_path = os.path.realpath(git_path)
			pos = abs_path.rfind("/")
			if pos!=-1:
				git_name = abs_path[pos+1:]
		return git_name
