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

from flask import current_app, abort
import connexion


def create_app(config=None):
    config = config or {}

    application = connexion.FlaskApp(
        __name__,
        specification_dir='openapi/',
        options={
            "swagger_ui": True
        }
    )
    application.add_api('pastrami.yml')

    with application.app.app_context():
        for key, value in config.items():
            application.app.config[key] = value

    try:
        application.debug = config['debug']
    except KeyError:
        pass

    return application

def get_text(text_id):
    '''Fetch a given resource'''
    database = current_app.config['__db_instance']
    result = database.text.query.get(text_id)
    if not result:
        abort(404, "Text '{}' doesn't exist".format(text_id))
    return result

def post_text(body):
    '''Create a new text'''
    database = current_app.config['__db_instance']
    text = database.text(text=body['text'])
    database.session.add(text)
    database.session.commit()
    return {'text': text.text, 'text_id': text.text_id, 'modified': text.modified}, 201
