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

import os
import sys

from schemed_yaml_config import get_config
from flask import current_app, abort, render_template, request, g, jsonify
import connexion

from pastrami.database import PastramiDB


# Application factory
def create_app(config=False):
    config = config or ""

    # Import config
    config_schema = os.path.join(os.path.dirname(__file__), 'config.yml')
    try:
        config = get_config(config, config_schema)
    except (IOError) as error:
        sys.exit(error)
    except (SyntaxError) as error:
        sys.exit(error)
    config = {k.upper(): v for k, v in config.items()}

    application = connexion.FlaskApp(
        __name__,
        specification_dir='openapi/',
        options={
            "swagger_ui": True
        }
    )
    application.add_api('pastrami.yml')
    application.app.config.from_mapping(**config)

    @application.route('/', methods=['GET'])
    @application.route('/<string:text_id>', methods=['GET'])
    def index_html(text_id=False):
        text = {}
        if text_id:
            if text_id.lower()[-4:] == '.txt':
                return text_html(text_id[:-4])
            text = get_content_by_id(text_id)
        return render_template('index.html', text=text)

    @application.route('/<string:text_id>', methods=['PUT'])
    def put_text(text_id=False):
        '''Create a new text'''
        database = get_db()

        body = request.data.decode("utf-8")
        text = database.text(text=body, text_id=text_id)
        try:
            database.session.add(text)
            database.session.commit()
        except DBIntegritiError:
            abort(409, "Duplicated text ID: %s" % text_id)

        result = jsonify({'text': text.text, 'text_id': text.text_id, 'modified': text.modified})
        return result, 201

    @application.route('/<string:text_id>/text')
    def text_html(text_id):
        text = get_content_by_id(text_id)
        return str(text), 200, {'Content-Type': 'text/plain'}

    def get_content_by_id(text_id):
        database = get_db()
        text = database.text.query.get(text_id)
        if not text:
            abort(404, "Text '{}' doesn't exist".format(text_id))

        return text

    return application


# Database shorthand
def get_db():
    if 'db' not in g:
        g.db = PastramiDB(current_app.config['DB'],)
    return g.db


# API Calls
def get_text(text_id):
    '''Fetch a given resource'''
    database = get_db()
    result = database.text.query.get(text_id)
    if not result:
        abort(404, "Text '{}' doesn't exist".format(text_id))
    return result

def post_text(body):
    '''Create a new text'''
    database = get_db()
    text = database.text(text=body['text'])
    database.session.add(text)
    database.session.commit()
    return {'text': text.text, 'text_id': text.text_id, 'modified': text.modified}, 201
