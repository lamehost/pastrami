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

from functools import wraps
from flask import request, current_app
from flask_restplus import abort

def request_auth(app):
    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            authkey = False
            if app:
                with app.app_context():
                    authkey = current_app.config['authkey']

            if authkey:
                try:
                    key, value = [
                        _.strip()
                        for _ in request.headers.get('Authorization', '').split(' ')
                    ]
                except ValueError:
                    key = False
                    value = False

                if key != 'AuthKey':
                    abort(401, "Unauthorized: Missing 'AuthKey'")
                elif value != authkey:
                    abort(401, 'Unauthorized AuthKey: %s' % value)


            return func(*args, **kwargs)
        return decorated
    return decorator
