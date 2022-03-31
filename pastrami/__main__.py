# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2022, Marco Marzetti <marco@lamehost.it>

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
    parser.add_argument(
        "port",
        metavar="PORT",
        default="8080",
        nargs='?',
        type=int,
        help="TCP port to bind to"
    )
    parser.add_argument(
        "config_file",
        metavar="FILE",
        default="pastrami.conf",
        nargs='?',
        help="configuration filename (default: pastrami.conf)"
    )
    args = parser.parse_args()

    application = create_app(args.config_file)
    debug = application.app.config['DEBUG']
    run_simple(
        args.host,
        args.port,
        application,
        use_reloader=debug,
        use_debugger=debug,
        use_evalex=debug
    )


if __name__ == "__main__":
    main()
