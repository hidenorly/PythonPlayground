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
import re
import subprocess
import sys
from ExecUtil import ExecUtil

class GitUtil:
	@staticmethod
	def changed_files(git_path, from_shaish, to_shaish, file_extensions, path_regexp=None, exclude_regexp=None):

		include_re = re.compile(path_regexp) if path_regexp else None
		exclude_re = re.compile(exclude_regexp) if exclude_regexp else None

		cmd = ["git", "diff", "--name-only", f"{from_shaish}..{to_shaish}"]

		try:
			out = subprocess.check_output(cmd, cwd=git_path, text=True)

			files = []
			for f in out.splitlines():
				if file_extensions and not f.endswith(tuple(file_extensions)):
					continue
				if include_re and not include_re.search(f):
					continue
				if exclude_re and exclude_re.search(f):
					continue

				files.append(f)
			return files
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
		abs_path = git_path
		if GitUtil.is_git_directory(git_path):
			abs_path = os.path.realpath(git_path)
		elif abs_path.endswith(".git"):
			abs_path = abs_path[0:-4]
		pos = abs_path.rfind("/")
		if pos!=-1:
			git_name = abs_path[pos+1:]
		return git_name

	@staticmethod
	def clone(git_clone_uri, clone_root_path, branch=None):
		if not os.path.exists(clone_root_path):
			os.makedirs(clone_root_path)

		cloned_path = os.path.join(clone_root_path, GitUtil.get_git_name(git_clone_uri))

		if GitUtil.is_git_directory(cloned_path):
			# Already cloned (the clone path contains the branch name, so
			# this directory is that branch's clone): refresh it in place
			# instead of silently reusing a stale snapshot -- discard any
			# local changes and fast-forward to the remote branch.
			if not branch:
				return cloned_path
			try:
				current = ExecUtil.exec_cmd_with_result(
					["git", "branch", "--show-current"], cloned_path).strip()
				if current != branch:
					try:
						ExecUtil.exec_cmd_with_result(
							["git", "checkout", branch], cloned_path)
					except subprocess.CalledProcessError:
						ExecUtil.exec_cmd_with_result(
							["git", "fetch", "origin", branch], cloned_path)
						ExecUtil.exec_cmd_with_result(
							["git", "checkout", branch], cloned_path)
				ExecUtil.exec_cmd_with_result(
					["git", "reset", "--hard"], cloned_path)
				ExecUtil.exec_cmd_with_result(
					["git", "pull", "origin", branch], cloned_path)
				return cloned_path
			except subprocess.CalledProcessError as e:
				print(f"ERROR: failed to update {cloned_path} (branch={branch}): {e.stderr.strip() if e.stderr else e}", file=sys.stderr)
				return None

		try:
			exec_cmd = [
				"git",
				"clone",
				git_clone_uri
			]
			if branch:
				exec_cmd.append("-b")
				exec_cmd.append(branch)
			ExecUtil.exec_cmd_with_result(exec_cmd, clone_root_path)
		except subprocess.CalledProcessError as e:
			# Do NOT swallow this: a missing branch (e.g. poky has no
			# 'wrynose' branch) must be visible to the caller, otherwise
			# the empty result is misread as "all components removed".
			print(f"ERROR: git clone {git_clone_uri} -b {branch} failed: {e.stderr.strip() if e.stderr else e}", file=sys.stderr)
			return None

		if GitUtil.is_git_directory(cloned_path):
			return cloned_path

		return None

	@staticmethod
	def pull(git_path, branch=None):
		if GitUtil.is_git_directory(git_path):
			try:
				exec_cmd = ["git", "pull"]
				ExecUtil.exec_cmd_with_result(exec_cmd, git_path)
			except:
				pass

	@staticmethod
	def log_from_to(git_path, before, after, pretty=None, grep=None, is_no_merges=True):
		result = ""
		if GitUtil.is_git_directory(git_path):
			exec_cmd_git_log = ["git", "log"]
			before = GitUtil.ensure_branch(git_path, before)
			after = GitUtil.ensure_branch(git_path, after)
			print(f"{git_path} {before} {after}")
			if pretty:
				exec_cmd_git_log.append(f"--pretty={pretty}")
			if before and after:
				exec_cmd_git_log.append(f"{before}..{after}")
			if is_no_merges:
				exec_cmd_git_log.append("--no-merges")
			if grep:
				exec_cmd_git_log.append("--regexp-ignore-case")
				exec_cmd_git_log.append("--extended-regexp")
				exec_cmd_git_log.append("--grep")
				exec_cmd_git_log.append(grep)

			result = ExecUtil.exec_cmd_with_result(exec_cmd_git_log, git_path)

		return str(result)


	@staticmethod
	def ensure_branch(git_path, branch):
		if GitUtil.is_git_directory(git_path):
			result = ""
			try:
				exec_cmd = ["git", "branch", "-a"]
				result = ExecUtil.exec_cmd_with_result(exec_cmd, git_path)
			except:
				pass
			for line in result.splitlines():
				pos = line.find("*")
				if pos!=-1:
					line = line[pos+1:].strip()
				pos = line.find(branch)
				if pos!=-1:
					return line.strip()
		return branch
