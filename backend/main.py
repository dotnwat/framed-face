import logging
from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from flask import request, jsonify, Flask
from flask import render_template, redirect

#
# TODO:
#  - figure out how to enable sockets instead of URLFetch
#    https://urllib3.readthedocs.io/en/latest/reference/urllib3.contrib.html
#
import requests
from requests_toolbelt.adapters import appengine
appengine.monkeypatch()

from secrets import SCALE_CALLBACK_TEST_AUTH_KEY

from models import ComparisonInputSet, ComparisonJobInputSet

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


@app.route('/callback', methods = ['POST'])
def callback():
    #
    # validate that the request has a correct scale authentication key. the
    # key is sent as a header with name Scale-Callback-Auth
    #
    # TODO:
    #  - how should both test and live keys be handled?
    #
    scale_auth_key = request.headers.get('Scale-Callback-Auth', None)
    if not scale_auth_key or scale_auth_key != SCALE_CALLBACK_TEST_AUTH_KEY:
        logging.warning("invalid scale auth key \"%s\" expected \"%s\"" % \
                (scale_auth_key, SCALE_CALLBACK_TEST_AUTH_KEY))
        return '', 401

    #
    # validate that the response has our metadata. we check again in the
    # worker, but want to avoid putting bad requests in the queue, and can
    # also respond to scale with an error.
    #
    # TODO:
    #  - validate json schema
    #
    data = request.get_json()
    if not data:
        logging.error("could not decode scale callback data: %s" % \
                (request.data,))
        return '', 500

    logging.info(`data`)

    taskqueue.add(url='/callback_worker',
            payload=request.data, target='worker')

    return '', 200

@app.route('/show/<key>', methods = ['GET'])
def show_task(key):
    task = ndb.Key(urlsafe=key).get()
    jobs = ComparisonJobInputSet.query(ancestor = task.key).fetch()
    return render_template('task.html', task=task, jobs=jobs)
#
# create a copy of a task and schedule processing
#
# TODO:
#  - only the source image urls are copied and we don't handle the case that
#    the source images are deleted or changed.
#
@ndb.transactional
def schedule_task_run(comparison_input):
    # create copy of input
    job_input_set = ComparisonJobInputSet(
            parent = comparison_input.key,
            img_urls = comparison_input.img_urls)
    job_input_key = job_input_set.put()

    # create the comparison job
    taskqueue.add(url='/create_comparison_job',
            params={'key': job_input_key.urlsafe()},
            target='worker',
            transactional=True)

#
# transactionally create a comparison task and optionally schedule task
# processing for the new task.
#
@ndb.transactional
def create_and_run_task(img_urls, schedule_run):
    task = ComparisonInputSet(img_urls = img_urls)
    key = task.put()
    if schedule_run:
        schedule_task_run(task)
    return key

#
# API: run a job
#
@app.route('/api/run', methods = ['POST'])
def run_task_route():
    key = ndb.Key(urlsafe = request.form['key'])
    task = key.get()
    schedule_task_run(task)
    return redirect('/show/' + key.urlsafe())

#
# API: create a job, and optionally run it
#
@app.route('/api/create', methods = ['POST'])
def create_task_route():
    img_urls = []
    for key, value in request.form.items():
        if "img" in key and value != '':
            img_urls.append(value)
    if img_urls == []:
        raise InvalidUsage('you must supply images', status_code=410)
    schedule_run = request.form.has_key('create-run')
    key = create_and_run_task(img_urls, schedule_run)
    return redirect('/show/' + key.urlsafe())

#
# VIEW: new task form
#
@app.route('/new', methods = ['GET'])
def new_task_route():
    return render_template('new.html')

@app.errorhandler(500)
def server_error(e):
    # Log the error and stacktrace.
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500
