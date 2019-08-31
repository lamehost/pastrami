# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2019, Marco Marzetti <marco@lamehost.it>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

from __future__ import absolute_import
from __future__ import print_function

import sys

from pastrami.config import get_config
from pastrami.database import PastramiDB
from pastrami.backend import create_app as backend
from pastrami.frontend import create_app as frontend


class DispatcherMiddleware():
    def __init__(self, app, mounts=None):
        self.app = app
        self.mounts = mounts or {}

    def __call__(self, environ, start_response):
        script = environ.get("PATH_INFO", "")

        while "/" in script:
            if script in self.mounts:
                app = self.mounts[script]
                break

            script = next(iter(script.rsplit("/", 1)))
        else:
            app = self.mounts.get(script, self.app)

        original_script_name = environ.get("SCRIPT_NAME", "")
        environ["SCRIPT_NAME"] = original_script_name + script
        # environ["PATH_INFO"] = path_info
        return app(environ, start_response)


def create_app(config_file='pastrami.conf'):
    config = {}
    try:
        config = get_config(config_file, 'config.yml')
    except (IOError) as error:
        sys.exit(error)
    except (SyntaxError) as error:
        print(error)
        sys.exit(1)

    config['__db_instance'] = PastramiDB(config['db'])

    app = DispatcherMiddleware(
        frontend(config), {
            '/api/2.0': backend(config)
        }
    )

    return app

