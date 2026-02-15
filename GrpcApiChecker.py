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
from typing import Dict, Set, List, Optional
import sys
from enum import Enum

@dataclass
class EnumValue:
    name: str
    number: int

@dataclass
class EnumDef:
    name: str
    values: Dict[int, EnumValue]  # number key

@dataclass
class FieldDef:
    name: str
    number: int
    type: str

@dataclass
class MessageDef:
    name: str
    fields: Dict[int, FieldDef]  # number key

@dataclass
class MethodDef:
    name: str
    number: Optional[int]
    input_type: str
    output_type: str

@dataclass
class ServiceDef:
    name: str
    methods: Dict[str, MethodDef]

@dataclass
class Schema:
    enums: Dict[str, EnumDef] = field(default_factory=dict)
    messages: Dict[str, MessageDef] = field(default_factory=dict)
    services: Dict[str, ServiceDef] = field(default_factory=dict)


class Compat:
    COMPATIBLE = "compatible"
    SOURCE = "source-compatible"
    INCOMPATIBLE = "incompatible"


class GrpcParser:
    # -- extractor/parser
    ENUM_RE = re.compile(r'enum\s+(\w+)\s*{([^}]*)}', re.S)
    ENUM_VALUE_RE = re.compile(r'(\w+)\s*=\s*(\d+)\s*;')

    MESSAGE_RE = re.compile(r'message\s+(\w+)\s*{([^}]*)}', re.S)
    FIELD_RE = re.compile(
        r'(optional|required|repeated)?\s*([\w\.]+)\s+(\w+)\s*=\s*(\d+)'
    )

    SERVICE_RE = re.compile(r'service\s+(\w+)\s*{([^}]*)}', re.S)
    RPC_RE = re.compile(
        r'rpc\s+(\w+)\s*\(([\w\.]+)\)\s*returns\s*\(([\w\.]+)\)'
    )

    @staticmethod
    def strip(text: str) -> str:
        return re.sub(r'//.*', '', text)

    @staticmethod
    def parse(text: str) -> Schema:
        text = GrpcParser.strip(text)
        schema = Schema()

        # enums
        for m in GrpcParser.ENUM_RE.finditer(text):
            name, body = m.groups()
            values = {}
            for v in GrpcParser.ENUM_VALUE_RE.finditer(body):
                vname, num = v.groups()
                num = int(num)
                values[num] = EnumValue(vname, num)
            schema.enums[name] = EnumDef(name, values)

        # messages
        for m in GrpcParser.MESSAGE_RE.finditer(text):
            name, body = m.groups()
            fields = {}
            for f in GrpcParser.FIELD_RE.finditer(body):
                _, ftype, fname, num = f.groups()
                num = int(num)
                fields[num] = FieldDef(fname, num, ftype)
            schema.messages[name] = MessageDef(name, fields)

        # services
        for m in GrpcParser.SERVICE_RE.finditer(text):
            name, body = m.groups()
            methods = {}
            for r in GrpcParser.RPC_RE.finditer(body):
                mname, inp, outp = r.groups()
                methods[mname] = MethodDef(
                    mname,
                    None,
                    inp,
                    outp
                )
            schema.services[name] = ServiceDef(name, methods)

        return schema


class ApiChecker:
    def __init__(self):
        self.incompatible: List[str] = []
        self.source_only: List[str] = []

    def check_enum(self, old: EnumDef, new: EnumDef):
        for num, oval in old.values.items():
            if num not in new.values:
                self.incompatible.append(
                    f"Enum {old.name}: value @{num} removed"
                )
                continue

            nval = new.values[num]
            if oval.name != nval.name:
                self.source_only.append(
                    f"Enum {old.name}: value name changed @{num} "
                    f"{oval.name} -> {nval.name}"
                )

    def check_message(self, old: MessageDef, new: MessageDef):
        for num, of in old.fields.items():
            if num not in new.fields:
                self.incompatible.append(
                    f"Message {old.name}: field @{num} removed"
                )
                continue

            nf = new.fields[num]

            if of.type != nf.type:
                self.incompatible.append(
                    f"Message {old.name}: field @{num} type changed "
                    f"{of.type} -> {nf.type}"
                )

            if of.name != nf.name:
                self.source_only.append(
                    f"Message {old.name}: field @{num} name changed "
                    f"{of.name} -> {nf.name}"
                )

    def check_service(self, old: ServiceDef, new: ServiceDef):
        for mname, om in old.methods.items():
            if mname not in new.methods:
                self.incompatible.append(
                    f"Service {old.name}: method '{mname}' removed"
                )
                continue

            nm = new.methods[mname]

            if om.number is not None and nm.number is not None:
                if om.number != nm.number:
                    self.incompatible.append(
                        f"{old.name}.{mname}: ordinal changed "
                        f"{om.number} -> {nm.number}"
                    )

            if om.input_type != nm.input_type:
                self.incompatible.append(
                    f"{old.name}.{mname}: input type changed "
                    f"{om.input_type} -> {nm.input_type}"
                )

            if om.output_type != nm.output_type:
                self.incompatible.append(
                    f"{old.name}.{mname}: output type changed "
                    f"{om.output_type} -> {nm.output_type}"
                )

    def check(self, old: Schema, new: Schema):
        # enums
        for name, e in old.enums.items():
            if name not in new.enums:
                self.incompatible.append(f"Enum '{name}' removed")
            else:
                self.check_enum(e, new.enums[name])

        # messages
        for name, m in old.messages.items():
            if name not in new.messages:
                self.incompatible.append(f"Message '{name}' removed")
            else:
                self.check_message(m, new.messages[name])

        # services
        for name, s in old.services.items():
            if name not in new.services:
                self.incompatible.append(f"Service '{name}' removed")
            else:
                self.check_service(s, new.services[name])

        # result
        if self.incompatible:
            return Compat.INCOMPATIBLE
        if self.source_only:
            return Compat.SOURCE
        return Compat.COMPATIBLE



def load_schema(path: str) -> Schema:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if path.endswith(".proto"):
        return GrpcParser.parse(text)

    raise ValueError("Unsupported file type")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: GrpcApiChecker.py OLD NEW")
        sys.exit(1)

    old = load_schema(sys.argv[1])
    new = load_schema(sys.argv[2])

    checker = ApiChecker()
    result = checker.check(old, new)

    if result == Compat.COMPATIBLE:
        print("API is backward compatible")
        sys.exit(0)

    if checker.source_only:
        print("Source-compatible changes detected:")
        for s in checker.source_only:
            print(" -", s)

    if checker.incompatible:
        print("Incompatible changes detected:")
        for i in checker.incompatible:
            print(" -", i)
        sys.exit(2)

    sys.exit(0)
