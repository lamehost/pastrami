# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import argparse

from werkzeug.serving import run_simple

from pastrami.webapp import create_app


def main():
    # Parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "host",
        metavar="HOST",
        default="0.0.0.0",
        nargs='?',
        help="Hostname to bind to"
    )
    args = parser.parse_args()
    parser.add_argument(
        "port",
        metavar="PORT",
        default="8080",
        nargs='?',
        type=int,
        help="TCP port to bind to"
    )
    args = parser.parse_args()
    parser.add_argument(
        "config",
        metavar="FILE",
        default="pastrami.conf",
        nargs='?',
        help="configuration filename (default: pastrami.conf)"
    )
    args = parser.parse_args()

    run_simple(
        args.host,
        args.port,
        create_app(args.config),
        use_reloader=True,
        use_debugger=True,
        use_evalex=True
    )


if __name__ == "__main__":
    main()
