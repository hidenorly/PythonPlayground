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


class Reporter:
	def __init__(self):
		pass

	def report(self, data, print_section_keys=[]):
		# check section, data structure
		if isinstance(data, dict):
			for section, section_data in data.items():
				self.print_section(section)

				# check data is array
				if isinstance(section_data, list):
					# check data is dict
					if isinstance(section_data[0], dict):
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
							self.print_line_dict_data(line_data, print_section_keys)

					# check data is array
					elif isinstance(section_data[0], list):
						if print_section_keys:
							self.print_section_keys(print_section_keys)
						for line_data in section_data:
							self.print_line_list_data(line_data)

	def print_section(self, section):
		print("")
		print(section)
		print("")

	def print_section_keys(self, section_keys):
		print(",".join(section_keys))

	def convert_array_to_multilines(self, col_data):
		result = ""
		for data in col_data:
			if result:
				result += ","
			if data:
				result += data
			else:
				result += " "

		return f'"{result}"'

	def print_line_dict_data(self, line_data, print_section_keys):
		print_str = ""
		for key in print_section_keys:
			if print_str:
				print_str += ","
			col = " "
			if key in line_data:
				col = line_data[key]
				if isinstance(col, list):
					col = self.convert_array_to_multilines(col)
			print_str += col
		print(print_str)

	def print_line_list_data(self, line_data):
		print_str = ""
		for col in line_data:
			if print_str:
				print_str += ","
			if col:
				if isinstance(col, list):
					col = self.convert_array_to_multilines(col)
				print_str += col
			else:
				print_str += " "
		print(print_str)


class MarkdownReporter(Reporter):
	def __init__(self):
		super().__init__()

	def print_section(self, section):
		print("")
		print(f"# {section}")
		print("")

	def print_section_keys(self, section_keys):
		print("| " + " | ".join(section_keys) + " |")
		print("| " + ":--- | "*len(section_keys))

	def convert_array_to_multilines(self, col_data):
		result = ""
		for data in col_data:
			if result:
				result += " <br> "
			if data:
				result += data

		return result

	def print_line_dict_data(self, line_data, print_section_keys):
		print_str = ""
		for key in print_section_keys:
			if print_str:
				print_str += " | "
			if key in line_data:
				col = line_data[key]
				if isinstance(col, list):
					col = self.convert_array_to_multilines(col)
				print_str += col
			else:
				print_str += " "
		print(f"| {print_str} |")

	def print_line_list_data(self, line_data):
		print_str = ""
		for col in line_data:
			if print_str:
				print_str += " | "
			if col:
				if isinstance(col, list):
					col = self.convert_array_to_multilines(col)
				print_str += col
			else:
				print_str += " "
		print(f"| {print_str} |")



if __name__=="__main__":

	dict_data = {
		"section_1":[
			{"key1":"data1_1", "key2":"data2_1", "key3":["data3_1", "data3_1_2", "data3_3"]},
			{"key1":"data1_2", "key2":"data2_2", "key4":"data3_2"}
		],
		"section_2":[
			{"key1":"data1_1", "key2":"data2_1", "key3":"data3_1"},
			{"key1":"data1_2", "key2":"data2_2", "key3":"data3_2"}
		]
	}

	array_data = {
		"section_1":[
			["data1_1", "data2_1", ["data3_1", "data3_1_2", "data3_3"]],
			["data1_2", "data2_2", "data3_2"],
		],
		"section_2":[
			["data1_1", "data2_1", "data3_1"],
			["data1_2", "data2_2", "data3_2"],
		]
	}


	report = Reporter()
	report.report(dict_data)
	report.report(array_data, ["key1","key2","key3"])

	report2 = MarkdownReporter()
	report2.report(dict_data)
	report2.report(array_data, ["key1","key2","key3"])
