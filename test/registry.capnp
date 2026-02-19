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

@0xcafecafecafecafe;

interface Callback {
  onUpdate @0 (key :Text, value :Text);
}

interface Registry {
  registerCallback @0 (cb :Callback) -> (id :UInt32);
  unregisterCallback @1 (id :UInt32);
  set @2 (key :Text, value :Text);
  get @3 (key :Text) -> (reply :Text);
}
