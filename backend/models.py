from google.appengine.ext import ndb

#
# ComparisonInputSet - a set of comparison items that can be modified.
#
class ComparisonInputSet(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    img_urls = ndb.StringProperty(repeated=True)

#
# imgN: index of the img url in img_urls
# dep0: index of the dependency task
# queued: queued creation of human task
# submitted: sent to human comp resource
#
class ComparisonTask(ndb.Model):
    queued = ndb.BooleanProperty(default=False)
    submitted = ndb.BooleanProperty(default=False)
    choice = ndb.IntegerProperty()
    img0 = ndb.IntegerProperty()
    dep0 = ndb.IntegerProperty()
    img1 = ndb.IntegerProperty()
    dep1 = ndb.IntegerProperty()

#
# ComparisonJobInputSet - a set of comparison items that are used as input to a
# job. in general this data is read-only, but might contain job-specific
# metdata.
#
class ComparisonJobInputSet(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    img_urls = ndb.StringProperty(repeated=True)
    tasks = ndb.LocalStructuredProperty(ComparisonTask, repeated=True)
