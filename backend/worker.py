import logging
from google.appengine.ext import ndb
from google.appengine.ext import deferred

from flask import request, jsonify, Flask
from flask import render_template, redirect

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
