# -*- coding: utf-8 -*-

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
                except (ValueError):
                    key = False
                    value = False

                if key != 'AuthKey':
                    abort(401, "Unauthorized: Missing 'AuthKey'")
                elif value != authkey:
                    abort(401, 'Unauthorized AuthKey: %s' % value)


            return func(*args, **kwargs)
        return decorated
    return decorator
