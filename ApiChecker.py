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
from clang.cindex import Config
import json
import platform

def load_libclang():
    candidates = [
        "/opt/homebrew/opt/llvm/lib/libclang.dylib",     # macOS Homebrew (arm64)
        "/usr/local/opt/llvm/lib/libclang.dylib",        # macOS Homebrew (x86)
        "/usr/lib/llvm-18/lib/libclang.so",              # Linux
        "/usr/lib/llvm-17/lib/libclang.so",
        "/usr/lib/llvm-16/lib/libclang.so",
    ]

    for path in candidates:
        try:
            Config.set_library_file(path)
            return path
        except Exception:
            pass

    raise RuntimeError("libclang not found")

# needs to load before importing other of clang.cindex
load_libclang()
from clang.cindex import Index, CursorKind


def detect_platform():
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")


def get_sysroot(os_type):
    if os_type == "macos":
        return subprocess.check_output(
            ["xcrun", "--show-sdk-path"], text=True
        ).strip()
    elif os_type == "linux":
        return None
    return None


def get_std_include_paths():
    cmd = ["clang++", "-E", "-x", "c++", "-", "-v"]
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _, err = p.communicate("")
    paths = []
    capture = False
    for line in err.splitlines():
        if "#include <...> search starts here:" in line:
            capture = True
            continue
        if "End of search list." in line:
            break
        if capture:
            paths.append(line.strip())
    return paths


def get_compile_args_from_db(header):
    try:
        with open("compile_commands.json") as f:
            db = json.load(f)
        for e in db:
            if header in e["file"]:
                return e["arguments"]
    except Exception:
        pass
    return None


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
    args = ["-x", "c++", "-std=c++20"]

    sysroot = get_sysroot(detect_platform())
    if sysroot:
        args.append(f"-isysroot{sysroot}")

    cc_args = get_compile_args_from_db(header)
    if cc_args:
        args = cc_args
    else:
        for p in get_std_include_paths():
            args.append(f"-I{p}")

    idx = Index.create()
    tu = idx.parse(header, args=args)

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
            "params": params
        }

    return api



def detect_breaking(old, new):
    removed = []
    changed = []
    added = []

    # removed case
    for f in old["functions"]:
        if f not in new["functions"]:
            removed.append( (f, old["functions"][f], None) )

    # signature change case
    for f, sig in new["functions"].items():
        if f in old["functions"] and sig != old["functions"][f]:
            old_func = old["functions"][f]
            new_func = new["functions"][f]
            changed.append((f, old_func, new_func))

    # just added case
    for f in new["functions"]:
        if f not in old["functions"]:
            added.append( (f, None, new["functions"][f]) )

    return removed, changed, added


def print_desc(desc, func, old_path, old, new_path, new):
    print(f"{desc} : {func}")
    print(f"\t{old_path}: {str(old)}")
    print(f"\t{new_path}: {str(new)}")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description='Api Check', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('args', nargs='*', help='old_file new_file')
    parser.add_argument('-a', '--added', action='store_true', default=False, help='If you want to dump added functions too')

    args = parser.parse_args()

    if len(args.args)==2:
        api_signatures = []
        for path in args.args:
            _signature = extract_c_api(path)
            api_signatures.append( _signature )
            #print(str(_signature))

        removed, changed, added = detect_breaking( api_signatures[0], api_signatures[1] )
        old_path = args.args[0]
        new_path = args.args[1]

        for a_break in removed:
            print_desc("Function removed", a_break[0], old_path, a_break[1], new_path, a_break[2])
        print("")
        for a_break in changed:
            print_desc("Signature changed", a_break[0], old_path, a_break[1], new_path, a_break[2])
        print("")
        if args.added:
            for a_break in added:
                print_desc("Function added", a_break[0], old_path, a_break[1], new_path, a_break[2])
