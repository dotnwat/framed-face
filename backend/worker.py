import logging
from google.appengine.ext import ndb
from google.appengine.ext import deferred

from flask import request, jsonify, Flask
from flask import render_template, redirect

from models import ComparisonInputSet, ComparisonJobInputSet

app = Flask(__name__)

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
    # retrieve the comparison input
    comparison_job_input_key = ndb.Key(urlsafe = request.form['key'])
    comparison_job_input = comparison_job_input_key.get()

    # generate bracket
    logging.info(comparison_job_input_key.urlsafe())

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
