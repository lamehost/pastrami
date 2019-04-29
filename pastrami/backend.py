# -*- coding: utf-8 -*-

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
