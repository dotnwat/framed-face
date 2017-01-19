from google.appengine.ext import ndb

#
# ComparisonInputSet - a set of comparison items that can be modified.
#
class ComparisonInputSet(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    img_urls = ndb.StringProperty(repeated=True)

#
# ComparisonJobInputSet - a set of comparison items that are used as input to a
# job. in general this data is read-only, but might contain job-specific
# metdata.
#
class ComparisonJobInputSet(ndb.Model):
    created = ndb.DateTimeProperty(auto_now_add=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    img_urls = ndb.StringProperty(repeated=True)
