/*
  Copyright (C) 2026 hidenorly

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

// no changed
void test_nochange(uint32_t input_arg);
// return change case
int test(uint32_t input_arg);
// signed/unsigned changed
void test2(int32_t input_arg);
// default arg
void test3(int32_t input_arg, int32_t input_arg2=0);
// added
void test4(int32_t input_arg);

