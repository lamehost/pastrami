# -*- coding: utf-8 -*-

# MIT License

# Copyright (c) 2024, Marco Marzetti <marco@lamehost.it>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

"""
Main entrypoint for the package
"""

import argparse

import uvicorn


def main() -> None:
    """
    Main package function.

    Starts uvicorn and runs `pastrami.create_app()`
    """

    # Parse CLI arguments
    parser = argparse.ArgumentParser(
        prog="pastrami",
        description="Secure pastebin web service.",
        epilog="Configuration file name is hardcoded: pastrami.conf",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="Turns uviconr debugging on"
    )
    parser.add_argument(
        "host",
        nargs="?",
        type=str,
        default="127.0.0.1",
        help="Host to bind to. Default: 127.0.0.1",
        metavar="HOST",
    )
    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=8080,
        help="Port to bind to. Default: 8080",
        metavar="PORT",
    )
    args = parser.parse_args()

    if args.debug:
        reload = True
        log_level = "debug"
    else:
        reload = False
        log_level = "warning"

    # Launch webapp through uvicorn
    uvicorn.run(
        "pastrami:create_app",
        host=args.host,
        port=args.port,
        log_level=log_level,
        reload=reload,
        factory=True,
        server_header=False,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
