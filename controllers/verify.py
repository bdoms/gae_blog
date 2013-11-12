import os
from datetime import datetime, timedelta
from hashlib import sha256

from google.appengine.api import memcache

from base import BaseController

SALT_KEY = "GAE_BLOG_VERIFY_SALT"

class VerifyController(BaseController):
    """ creates a token to help verify a form submission """

    def get(self):

        # send along a token so we can verify this request
        referer = self.request.headers.get("referer")
        if not referer.startswith("http://" + self.request.headers.get("host")):
            self.renderError(400)

        url = self.request.get("url")

        self.renderJSON({'token': generateToken(url)})


def generateToken(url, again=False):
    salt = memcache.get(SALT_KEY)
    if not salt:
        salt = os.urandom(64)
        memcache.set(SALT_KEY, salt)
    now = datetime.utcnow()
    if again:
        now -= timedelta(minutes=1)
    return sha256(url + now.strftime("%Y%m%d%H%M")).hexdigest()
