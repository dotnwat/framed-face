import logging
from itertools import izip
from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from flask import request, jsonify, Flask
from flask import render_template, redirect

from models import ComparisonInputSet, ComparisonJobInputSet, ComparisonTask

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

def grouped(iterable):
    groups = list(izip(*[iter(iterable)]*2))
    if len(iterable) % 2 == 0:
        return groups, None
    return groups, list(iterable)[-1]

#
# TODO: queueing work from the scaleapi callback keeps latency low and
# predictable for the callback handler, but processing the queue doesn't
# address the throughput limitations of updating entity groups because each
# update is still handled one-at-a-time. a solution to this problem is the use
# of pull queues which let requests be tagged (e.g. by ancestor) and then a
# batch of tasks for an entity group can be requested and handled together.
#
@app.route('/callback_worker', methods = ['POST'])
def callback_worker():
    logging.info(request.data)
    return '', 200

#
#
#
@ndb.transactional
def do_handle_create_task(urlsafe_key):
    # retrieve the comparison input
    comparison_job_input_key = ndb.Key(urlsafe = urlsafe_key)
    comparison_job_input = comparison_job_input_key.get()

    # todo:
    # - check return codes
    # - eliminate duplicates (model validator)
    # - use model validator for img urls length?
    img_urls = comparison_job_input.img_urls
    if len(img_urls) < 2:
        raise InvalidUsage('img urls too small', 410)
    if len(comparison_job_input.tasks) > 0:
        raise InvalidUsage('tasks should be empty', 410)

    # generate tasks. tasks may have dependencies on other tasks which are
    # represented by an index into the array of tasks. it would be good to
    # represent parent pointers so that we don't need to scan the data
    # structure when an update is made (to find those that depend on the
    # updated task). for small jobs this will work just fine.
    prev_task = None
    groups, extra = grouped(range(len(img_urls)))
    for url0, url1 in groups:
        task = ComparisonTask(img0=url0, img1=url1)
        comparison_job_input.tasks.append(task)
        if prev_task is None:
            prev_task = len(comparison_job_input.tasks) - 1
            continue
        task = ComparisonTask(dep0=prev_task,
                dep1 = len(comparison_job_input.tasks) - 1)
        comparison_job_input.tasks.append(task)
        prev_task = len(comparison_job_input.tasks) - 1
    if extra:
        task = ComparisonTask(dep0=prev_task, img1=extra)
        comparison_job_input.tasks.append(task)

    comparison_job_input.put()

    taskqueue.add(url='/dispatch_comparison_tasks',
            params={'key': urlsafe_key},
            target='worker',
            transactional=True)

#
# SERVICE: create comparison job
#
# 1. retrieve the comparison input
# 2. select a comparison strategy (or default)
# 3. transactionlly
#      1. generate the comparison bracket
#      2. schedule work to process comparison
#
# - current limitations: we only support strategies that can generate a full
# comparison bracket (rather than an iterative approach that depends on
# intermediate results). we also limit the size of the bracket because the
# entire bracket is saved in a single transaction.
#
@app.route('/create_comparison_job', methods = ['POST'])
def handle_create_task():
    do_handle_create_task(request.form['key'])
    return '', 200

@ndb.transactional
def dispatch_some_tasks(urlsafe_key):
    job = ndb.Key(urlsafe = urlsafe_key).get()
    more_tasks = False
    tasks_queued = 0
    for i in range(len(job.tasks)):
        if job.tasks[i].queued or job.tasks[i].submitted:
            if job.tasks[i].submitted:
                logging.warning("trying to dispatch submitted task")
            continue
        if job.tasks[i].img0 != None and job.tasks[i].img1 != None:
            taskqueue.add(url='/submit_comparison_task',
                    params={'key': urlsafe_key,
                            'idx': i,
                            'img0': job.img_urls[job.tasks[i].img0],
                            'img1': job.img_urls[job.tasks[i].img1]},
                    target='worker',
                    transactional=True)
            job.tasks[i].queued = True
            tasks_queued += 1
            if tasks_queued == 5:
                more_tasks = True
                break
            pass
        pass
    job.put()
    return more_tasks

@app.route('/dispatch_comparison_tasks', methods = ['POST'])
def handle_dispatch_comparison_tasks():
    urlsafe_key = request.form['key']
    while dispatch_some_tasks(urlsafe_key):
        pass
    return '', 200

@app.route('/submit_comparison_task', methods = ['POST'])
def handle_submit_comparison_task():
    logging.info(request.form)
    return '', 200

## must be a valid url. we don't want to rely on scaleapi here. so we
## create a new comparison task and transactionally also add it to the
## queue. then the queue will take care of contacting scale.
#import scaleapi
#client = scaleapi.ScaleClient('test_662e9c151e955479bb8bd4363e223467')
#client.create_comparison_task(
#        callback_url='https://focus-vertex-155920.appspot.com/callback',
#        instruction='Do the objects in these images have the same pattern?',
#                attachment_type='image',
#                attachments=img_urls,
#                choices=['yes', 'no']
#                )
