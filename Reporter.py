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

import os


# data = {
#	section_1:[
#		{key1:data1_1, key2:data2_1, key3:data3_1},
#		{key1:data1_2, key2:data2_2, key3:data3_2},
#		...
#	],
#	section_2:[
#	]
# }


class Reporter:
	def __init__(self):
		pass

	def report(self, data, print_section_keys=[]):
		for section, section_data in data.items():
			self.print_section(section)

			# extract col keys
			section_keys_ = set()
			section_keys = []
			for line_data in section_data:
				for key, col in line_data.items():
					if not key in section_keys_:
						section_keys_.add(key)
						section_keys.append(key)
			# dump cols
			if not print_section_keys:
				print_section_keys = section_keys
			self.print_section_keys(print_section_keys)

			# dump data
			for line_data in section_data:
				self.print_line_data(line_data, print_section_keys)


	def print_section(self, section):
		print("")
		print(section)
		print("")

	def print_section_keys(self, section_keys):
		print(",".join(section_keys))

	def print_line_data(self, line_data, print_section_keys):
		print_str = ""
		for key in print_section_keys:
			if print_str:
				print_str += ","
			if key in line_data:
				print_str += f"{line_data[key]}"
			else:
				print_str += " "
		print(print_str)



if __name__=="__main__":

	data = {
		"section_1":[
			{"key1":"data1_1", "key2":"data2_1", "key3":"data3_1"},
			{"key1":"data1_2", "key2":"data2_2", "key4":"data3_2"}
		],
		"section_2":[
			{"key1":"data1_1", "key2":"data2_1", "key3":"data3_1"},
			{"key1":"data1_2", "key2":"data2_2", "key3":"data3_2"}
		]
	}

	report = Reporter()
	report.report(data)
