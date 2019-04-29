# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import sys

from pastrami.configuration import get_config
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
        config = get_config(config_file, 'configuration/pastrami.yml')
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


application = create_app()
