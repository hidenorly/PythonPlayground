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

#!/usr/bin/env python3
import os
import re
from dataclasses import dataclass, field
from typing import Dict, Set, List
import sys

@dataclass
class EnumValue:
    name: str
    ordinal: int

@dataclass
class EnumDef:
    name: str
    values: Dict[str, EnumValue]

@dataclass
class StructField:
    ordinal: int
    type: str

@dataclass
class StructDef:
    name: str
    fields: dict[int, StructField]

@dataclass
class Field:
    type: str

@dataclass
class Method:
    name: str
    ordinal: int
    params: list[Field]
    results: list[Field]

@dataclass
class InterfaceDef:
    name: str
    methods: Dict[str, Method]

@dataclass
class Schema:
    enums: dict[str, EnumDef] = field(default_factory=dict)
    interfaces: dict[str, InterfaceDef] = field(default_factory=dict)
    structs: dict[str, StructDef] = field(default_factory=dict)



class CapnApiChecker:
    # -- extractor/parser
    IMPORT_RE = re.compile(r'import\s+"([^"]+)"\s*;')

    ENUM_RE = re.compile(
        r'enum\s+(\w+)\s*{([^}]*)}', re.S)

    ENUM_VALUE_RE = re.compile(
        r'(\w+)\s*@\s*(\d+)\s*;')

    STRUCT_RE = re.compile(
        r'struct\s+(\w+)\s*{([^}]*)}', re.S
    )

    STRUCT_FIELD_RE = re.compile(
        r'(\w+)\s*@\s*(\d+)\s*:\s*([\w\.]+)\s*;'
    )

    INTERFACE_RE = re.compile(
        r'interface\s+(\w+)\s*(?:@\s*0x[0-9a-fA-F]+)?\s*{([^}]*)}',
        re.S
    )

    METHOD_RE = re.compile(
        r'(\w+)\s*@\s*(\d+)\s*'
        r'\(([^)]*)\)\s*'
        r'(?:->\s*\(([^)]*)\))?\s*;',
        re.S
    )

    FIELD_RE = re.compile(
        r'(\w+)\s*:\s*([\w\.]+)')

    def strip_comments(text: str) -> str:
        text = re.sub(r'//.*', '', text)
        text = re.sub(r'#.*', '', text)
        return text

    def extract_imports(text: str) -> List[str]:
        return CapnApiChecker.IMPORT_RE.findall(text)

    def parse_fields(text: str) -> list[Field]:
        fields = []
        for m in CapnApiChecker.FIELD_RE.finditer(text):
            _, type_ = m.groups()
            fields.append(Field(type_))
        return fields

    def parse_enums(text: str, schema: Schema):
        for m in CapnApiChecker.ENUM_RE.finditer(text):
            name, body = m.groups()
            values = {}
            for v in CapnApiChecker.ENUM_VALUE_RE.finditer(body):
                vname, ordinal = v.groups()
                values[vname] = EnumValue(vname, int(ordinal))
            schema.enums[name] = EnumDef(name, values)

    def parse_structs(text: str, schema: Schema):
        for m in CapnApiChecker.STRUCT_RE.finditer(text):
            name, body = m.groups()
            fields = {}
            for f in CapnApiChecker.STRUCT_FIELD_RE.finditer(body):
                _, ordinal, type_ = f.groups()
                ordinal = int(ordinal)
                fields[ordinal] = StructField(ordinal, type_)
            schema.structs[name] = StructDef(name, fields)

    def parse_interfaces(text: str, schema: Schema):
        for m in CapnApiChecker.INTERFACE_RE.finditer(text):
            name, body = m.groups()
            methods = {}

            for mm in CapnApiChecker.METHOD_RE.finditer(body):
                mname, ordinal, params, results = mm.groups()
                methods[mname] = Method(
                    name=mname,
                    ordinal=int(ordinal),
                    params=CapnApiChecker.parse_fields(params),
                    results=CapnApiChecker.parse_fields(results or ""),
                )

            schema.interfaces[name] = InterfaceDef(name, methods)

    def parse_capnp(text: str) -> Schema:
        text = CapnApiChecker.strip_comments(text)
        schema = Schema()
        CapnApiChecker.parse_enums(text, schema)
        CapnApiChecker.parse_structs(text, schema)
        CapnApiChecker.parse_interfaces(text, schema)
        return schema

    def resolve_import_path(current_file: str, import_path: str) -> str:
        base = os.path.dirname(os.path.abspath(current_file))
        resolved = os.path.normpath(os.path.join(base, import_path))
        if not os.path.isfile(resolved):
            raise FileNotFoundError(
                f"Import not found: {import_path} (from {current_file})"
            )
        return resolved

    def load_schema(path: str, visited: Set[str] | None = None) -> Schema:
        if visited is None:
            visited = set()

        path = os.path.abspath(path)
        if path in visited:
            return Schema()

        visited.add(path)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        schema = CapnApiChecker.parse_capnp(text)

        for imp in CapnApiChecker.extract_imports(text):
            imp_path = CapnApiChecker.resolve_import_path(path, imp)
            sub = CapnApiChecker.load_schema(imp_path, visited)
            schema.enums.update(sub.enums)
            schema.interfaces.update(sub.interfaces)

        return schema

    # -- checker
    def check_enum(old: EnumDef, new: EnumDef, errors: List[str]):
        for name, oval in old.values.items():
            if name not in new.values:
                errors.append(
                    f"Enum {old.name}: value '{name}' removed"
                )
            else:
                nval = new.values[name]
                if oval.ordinal != nval.ordinal:
                    errors.append(
                        f"Enum {old.name}.{name}: ordinal changed "
                        f"{oval.ordinal} -> {nval.ordinal}"
                    )

    def check_struct(old: StructDef, new: StructDef, errors: List[str]):
        for ord_, field in old.fields.items():
            if ord_ not in new.fields:
                errors.append(
                    f"struct {old.name}: field @{ord_} removed"
                )
            else:
                nf = new.fields[ord_]
                if field.type != nf.type:
                    errors.append(
                        f"struct {old.name}: field @{ord_} type changed "
                        f"{field.type} -> {nf.type}"
                    )

    def check_method(old: Method, new: Method, iface: str, errors: list[str]):
        if old.ordinal != new.ordinal:
            errors.append(
                f"{iface}.{old.name}: ordinal changed "
                f"{old.ordinal} -> {new.ordinal}"
            )

        if len(old.params) > len(new.params):
            errors.append(
                f"{iface}.{old.name}: parameters removed"
            )

        for i, p in enumerate(old.params):
            np = new.params[i]
            if p.type != np.type:
                errors.append(
                    f"{iface}.{old.name}: param[{i}] type changed "
                    f"{p.type} -> {np.type}"
                )

        if len(old.results) > len(new.results):
            errors.append(
                f"{iface}.{old.name}: results removed"
            )

        for i, r in enumerate(old.results):
            nr = new.results[i]
            if r.type != nr.type:
                errors.append(
                    f"{iface}.{old.name}: result[{i}] type changed "
                    f"{r.type} -> {nr.type}"
                )

    def check_interface(old: InterfaceDef, new: InterfaceDef, errors: List[str]):
        for mname, m in old.methods.items():
            if mname not in new.methods:
                errors.append(
                    f"Interface {old.name}: method '{mname}' removed"
                )
            else:
                CapnApiChecker.check_method(m, new.methods[mname], old.name, errors)

    def check_compat(old: Schema, new: Schema) -> List[str]:
        errors = []

        for ename, e in old.enums.items():
            if ename not in new.enums:
                errors.append(f"Enum '{ename}' removed")
            else:
                CapnApiChecker.check_enum(e, new.enums[ename], errors)

        for iname, i in old.interfaces.items():
            if iname not in new.interfaces:
                errors.append(f"Interface '{iname}' removed")
            else:
                CapnApiChecker.check_interface(i, new.interfaces[iname], errors)

        return errors


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: capnp_compat.py OLD.capnp NEW.capnp")
        sys.exit(1)

    old_path, new_path = sys.argv[1], sys.argv[2]

    old_schema = CapnApiChecker.load_schema(old_path)
    new_schema = CapnApiChecker.load_schema(new_path)

    print(f"{old_path} {new_path}")

    errors = CapnApiChecker.check_compat(old_schema, new_schema)

    if errors:
        print("Incompatible changes detected:")
        for e in errors:
            print(" -", e)
        sys.exit(2)
    else:
        print("API is backward compatible")

