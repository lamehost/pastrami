# -*- coding: utf-8 -*-

from __future__ import absolute_import

from flask import Flask, render_template, current_app, abort, request, jsonify

from pastrami.database import DBIntegritiError


def create_app(config=None):
    application = Flask(__name__)

    with application.app_context():
        for key, value in config.items():
            application.config[key] = value

    try:
        application.debug = config['debug']
    except KeyError:
        pass

    @application.route('/', methods=['GET'])
    @application.route('/<string:text_id>', methods=['GET'])
    def index_html(text_id=False):
        text = {}
        if text_id:
            text = get_content_by_id(text_id)
        return render_template('index.html', text=text)

    @application.route('/<string:text_id>', methods=['PUT'])
    def put_text(text_id=False):
        '''Create a new text'''
        database = current_app.config['__db_instance']

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
        return str("<pre>%s</pre>" % text)

    def get_content_by_id(text_id):
        database = current_app.config['__db_instance']
        text = database.text.query.get(text_id)
        if not text:
            abort(404, "Text '{}' doesn't exist".format(text_id))

        return text

    return application
