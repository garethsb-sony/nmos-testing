# Copyright (C) 2018 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import time

class Test(object):
    def __init__(self, description, name=None):
        self.description = description
        self.name = name
        if not self.name:
            # Get name of calling function
            self.name = inspect.stack()[1][3]
        self.timer = time.time()

    def _time_elapsed(self):
        return "{0:.3f}s".format(time.time() - self.timer)

    def PASS(self, detail=""):
        return [self.description, "Pass", detail, self.name, self._time_elapsed()]

    def MANUAL(self, detail=""):
        return [self.description, "Manual", detail, self.name, self._time_elapsed()]

    def NA(self, detail):
        return [self.description, "N/A", detail, self.name, self._time_elapsed()]

    def FAIL(self, detail):
        return [self.description, "Fail", detail, self.name, self._time_elapsed()]
