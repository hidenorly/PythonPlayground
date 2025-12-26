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

# pip install clang

import argparse
import subprocess
sdk_path = subprocess.check_output(
    ["xcrun", "--show-sdk-path"], text=True
).strip()
from clang.cindex import Config
Config.set_library_file("/opt/homebrew/opt/llvm/lib/libclang.dylib")
from clang.cindex import Index, CursorKind


from clang.cindex import CursorKind

def has_default_arg(param_cursor):
    for c in param_cursor.get_children():
        if c.kind in (
            CursorKind.INTEGER_LITERAL,
            CursorKind.CXX_BOOL_LITERAL_EXPR,
            CursorKind.FLOATING_LITERAL,
            CursorKind.STRING_LITERAL,
            CursorKind.UNEXPOSED_EXPR,
            CursorKind.CXX_NULL_PTR_LITERAL_EXPR,
        ):
            return True
    return False



def extract_c_api(header):
    idx = Index.create()
    tu = idx.parse(
        header,
        args=[
            "-x", "c++",
            "-std=c++20",
            f"-isysroot{sdk_path}",
            "-I/opt/homebrew/opt/llvm/include/c++/v1",
        ],
    )

    api = {"functions": {}}

    for c in tu.cursor.walk_preorder():
        if c.kind not in (
            CursorKind.FUNCTION_DECL,
            CursorKind.CXX_METHOD,
        ):
            continue

        name = c.spelling
        ret_type = c.result_type.get_canonical().spelling

        params = []
        for a in c.get_arguments():
            params.append({
                "type": a.type.get_canonical().spelling,
                "required": not has_default_arg(a),
            })

        api["functions"][name] = {
            "return": ret_type,
            "params": params,
            "location": str(c.location.file),
        }

    return api




def detect_breaking(old, new):
    breaking = []

    for f in old["functions"]:
        if f not in new["functions"]:
            breaking.append(f"Function removed: {f}")

    for f, sig in new["functions"].items():
        if f in old["functions"] and sig != old["functions"][f]:
            old_func = old["functions"][f] if f in old["functions"] else None
            new_func = new["functions"][f] if f in new["functions"] else None
            breaking.append((f"Signature changed: {f}", old_func, new_func))

    return breaking


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Api Check', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('args', nargs='*', help='old_file new_file')
    #parser.add_argument('-t', '--target', action='store', default="./yocto_components", help='specify git clone root')

    args = parser.parse_args()

    if len(args.args)==2:
        api_signatures = []
        for path in args.args:
            _signature = extract_c_api(path)
            api_signatures.append( _signature )
            #print(str(_signature))

        breakings = detect_breaking( api_signatures[0], api_signatures[1] )

        for a_break in breakings:
            print(a_break[0])
            print(f"\told: {str(a_break[1])}")
            print(f"\tnew: {str(a_break[2])}")
