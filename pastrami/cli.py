# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import argparse
import sys

from flask import current_app

from pastrami.configuration import get_config
from pastrami.pastrami import APP


def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "config",
        metavar="FILE",
        default="pastrami.conf",
        nargs='?',
        help="configuration filename (default: pastrami.conf)"
    )
    args = parser.parse_args()

    # Read configuration
    config = {}
    try:
        config = get_config(args.config)
    except (IOError) as error:
        sys.exit(error)
    except (SyntaxError) as error:
        print(error)
        sys.exit(1)

    with APP.app_context():
        for key, value in config.items():
            current_app.config[key] = value

    APP.run(
        debug=config['debug'],
        host=config['host'],
        port=config['port']
    )


if __name__ == "__main__":
    main()
