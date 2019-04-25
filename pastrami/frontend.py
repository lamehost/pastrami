# -*- coding: utf-8 -*-

from __future__ import absolute_import

from flask import Flask, render_template, current_app, abort

from pastrami.database import PastramiDB, DBIntegritiError

def create_app(config=None):
    application = Flask(__name__)

    with application.app_context():
        for key, value in config.items():
            application.config[key] = value

    application.config['PastramiDB'] = PastramiDB(**application.config['db'])

    @application.route('/')
    @application.route('/<string:text_id>')
    def index_html(text_id=False):
        text = {}
        if text_id:
            text = get_content_by_id(text_id)
        return render_template('index.html', text=text)

    @application.route('/<string:text_id>/text')
    def text_html(text_id):
        text = get_content_by_id(text_id)
        return str("<pre>%s</pre>" % text)

    def get_content_by_id(text_id):
        database = current_app.config['PastramiDB']
        text = database.text.query.get(text_id)
        if not text:
            abort(404, "Text '{}' doesn't exist".format(text_id))

        return text

    return application
