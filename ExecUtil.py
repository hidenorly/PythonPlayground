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

class ExecUtil:
    @staticmethod
    def exec_cmd_with_result(exec_cmd, exec_path):
        if not os.path.exists(exec_path):
            os.makedirs(exec_path)

        result = subprocess.run(
            exec_cmd,
            cwd=exec_path,
            check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return str(result.stdout)

