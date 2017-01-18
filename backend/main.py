import logging
from google.appengine.ext import ndb

from flask import request, jsonify, Flask
from flask import render_template, redirect

from secrets import SCALE_CALLBACK_AUTH_KEY

app = Flask(__name__)

class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

class ComparisonTask(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    img_urls = ndb.StringProperty(repeated=True)

@app.route('/callback', methods = ['POST'])
def callback():
    # validate the scale auth key attached to the request
    scale_auth_key = request.headers.get('Scale-Callback-Auth', None)
    if not scale_auth_key or scale_auth_key != SCALE_CALLBACK_AUTH_KEY:
        logging.warning("bad scale auth key \"%s\" expected \"%s\"" % \
                (scale_auth_key, SCALE_CALLBACK_AUTH_KEY))
        return '', 401
    return '', 201

@app.route('/show/<key>', methods = ['GET'])
def show_task(key):
    task = ndb.Key(urlsafe=key).get()
    return render_template('task.html', task=task)

def create_new_comparison_task(request):
    img_urls = []
    for key, value in request.form.items():
        if "img" in key and value != '':
            img_urls.append(value)
    if img_urls == []:
        raise InvalidUsage('you must supply images', status_code=410)

    task = ComparisonTask(img_urls = img_urls)
    key = task.put()

    return redirect('/show/' + key.urlsafe())

@app.route('/new', methods = ['GET', 'POST'])
def new_task():
    if request.method == 'GET':
        return render_template('new.html')
    elif request.method == 'POST':
        return create_new_comparison_task(request)

@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
