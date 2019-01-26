# -*- coding: utf-8 -*-

from __future__ import absolute_import

from datetime import datetime, timedelta

from flask import Flask, render_template, current_app
from flask_restplus import Api, Resource, fields, abort

from pastrami.authentication import request_auth
from pastrami.database import PastramiDB

# Init Flask App
APP = Flask(__name__)

# Get Database Handler
def get_database_handler():
    with APP.app_context():
        try:
            database = current_app.config['PastramiDB']
        except KeyError:
            database = PastramiDB(**current_app.config['db'])
            current_app.config['PastramiDB'] = database

    return database


# HTML Routes
def get_content_by_id(text_id):
    database = get_database_handler()
    text = database.text.query.get(text_id)
    if not text:
        abort(404, "Text '{}' doesn't exist".format(text_id))

    return text

@APP.route('/')
@APP.route('/<text_id>')
def index_html(text_id=False):
    text = {}
    if text_id:
        text = get_content_by_id(text_id)
    return render_template('index.html', text=text)

@APP.route('/<text_id>/text')
def text_html(text_id):
    text = get_content_by_id(text_id)
    return str("<pre>%s</pre>" % text)


# Init APIs
API = Api(
    APP,
    version='1.0',
    title='Pastrami',
    description='A text paste service',
    doc='/doc/',
    authorizations={
        'AuthKey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    }
)
NAMESPACE = API.namespace('api', description='Text operations')

# Data model for API 1.0
TEXTV10 = API.model('Text', {
    'text_id': fields.String(
        readOnly=True,
        required=False,
        description='Text unique identifier'
    ),
    'text': fields.String(
        required=True,
        description='Text content'
    ),
    'modified': fields.DateTime(
        readOnly=True,
        required=False,
        description='Last time text has been modified',
        dt_format='iso8601'
    )
})

@NAMESPACE.route('/1.0/')
class TextList(Resource):
    '''Shows a list of all texts, and lets you POST to add new text'''
    @NAMESPACE.doc('list_text')
    @NAMESPACE.marshal_list_with(TEXTV10)
    @request_auth(app=APP)
    def get(self):
        '''List all texts'''
        database = get_database_handler()
        return database.text.query.all()

    @NAMESPACE.doc('create_text')
    @NAMESPACE.expect(TEXTV10)
    @NAMESPACE.marshal_with(TEXTV10, code=201)
    def post(self):
        '''Create a new text'''
        database = get_database_handler()
        payload = API.payload
        text = database.text(text=payload['text'])
        database.session.add(text)
        database.session.commit()
        return text, 201


@NAMESPACE.route('/1.0/<string:text_id>')
@NAMESPACE.response(404, 'Text not found')
@NAMESPACE.param('text_id', 'Text unique identifier')
class Text(Resource):
    '''Show a single text item and lets you delete them'''
    @NAMESPACE.doc('get_text')
    @NAMESPACE.marshal_with(TEXTV10)
    def get(self, text_id):
        return self._get(text_id)

    @staticmethod
    def _get(text_id):
        '''Fetch a given resource'''
        database = get_database_handler()
        result = database.text.query.get(text_id)
        if not result:
            abort(404, "Text '{}' doesn't exist".format(text_id))
        return result

    @NAMESPACE.doc('delete_text')
    @request_auth(app=APP)
    def delete(self, text_id):
        '''Delete a text given its identifier'''
        database = get_database_handler()
        with APP.app_context():
            dayspan = current_app.config['dayspan']
        # Delete ALL posts older than dayspan
        result = ""
        if text_id == '__OLD__' and dayspan:
            epoch = datetime.utcnow() - timedelta(days=dayspan)
            for text in database.text.query.filter(database.text.modified <= epoch):
                database.session.delete(text)
            database.session.commit()
            result = "Texts older than {} deleted".format(epoch)
        # Delete by ID
        else:
            text = self._get(text_id)
            database.session.delete(text)
            database.session.commit()
            result = "Text '{}' deleted".format(text_id)
        return result, 200

    @NAMESPACE.expect(TEXTV10)
    @NAMESPACE.marshal_with(TEXTV10)
    @request_auth(app=APP)
    def put(self, text_id):
        '''Update a text given its identifier'''
        database = get_database_handler()
        text = self._get(text_id)
        payload = API.payload
        text.text = payload['text']
        database.session.commit()
        return text
