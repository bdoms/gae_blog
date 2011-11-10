
import re
from time import mktime
from datetime import datetime

from google.appengine.ext import db, blobstore
from google.appengine.api import images

MB = 1000000 # really 1048000 (2**20), but Google turns sets the limit artificially


# standard model objects
class Blog(db.Model):

    title = db.StringProperty()
    description = db.StringProperty()
    comments = db.BooleanProperty(default=False)
    moderation_alert = db.BooleanProperty(default=False)
    contact = db.BooleanProperty(default=False)
    admin_email = db.StringProperty()
    posts_per_page = db.IntegerProperty(default=10)
    image_preview_width = db.IntegerProperty(default=600)
    image_preview_height = db.IntegerProperty(default=600)
    url = db.StringProperty(default='/blog')
    template = db.StringProperty()
    blocklist = db.ListProperty(str)

    @property
    def published_posts(self):
        return self.posts.filter('published =', True).filter('timestamp <', datetime.utcnow()).order('-timestamp')


class BlogAuthor(db.Model):

    name = db.StringProperty(required=True)
    slug = db.StringProperty(required=True)
    url = db.StringProperty()
    email = db.StringProperty()
    blog = db.ReferenceProperty(Blog, required=True, collection_name="authors")

    @property
    def published_posts(self):
        return self.posts.filter('published =', True).filter('timestamp <', datetime.utcnow()).order('-timestamp')


class BlogPost(db.Model):

    title = db.StringProperty(required=True) # max of 500 chars
    slug = db.StringProperty(required=True)
    body = db.TextProperty() # returns type db.Text (a subclass of unicode)
    published = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    author = db.ReferenceProperty(BlogAuthor, required=True, collection_name="posts")
    blog = db.ReferenceProperty(Blog, required=True, collection_name="posts")

    @property
    def approved_comments(self):
        return self.comments.filter('approved =', True).order('timestamp')

    @property
    def secondsSinceEpoch(self):
        return mktime(self.timestamp.timetuple())

    def summarize(self, length):
        # returns a copy of the body truncated to the specified number of words
        no_html = stripHTML(self.body)
        words = no_html.split(" ")
        if len(words) <= length:
            return no_html
        else:
            return " ".join(words[:length]) + "..."


class BlogComment(db.Model):

    name = db.StringProperty()
    url = db.StringProperty()
    email = db.StringProperty()
    body = db.TextProperty(required=True)
    approved = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    ip_address = db.StringProperty(default='')
    post = db.ReferenceProperty(BlogPost, required=True, collection_name="comments")
    author = db.ReferenceProperty(BlogAuthor, collection_name="comments")

    def __init__(self, *args, **kwargs):
        assert "email" in kwargs or "author" in kwargs, "A BlogComment needs either an email address or attached author for verification."
        return super(BlogComment, self).__init__(*args, **kwargs)

    @property
    def secondsSinceEpoch(self):
        return mktime(self.timestamp.timetuple())


class BlogImage(db.Model):

    blog = db.ReferenceProperty(Blog, required=True, collection_name="images")
    blob = blobstore.BlobReferenceProperty(required=True)

    @property
    def url(self):
        return images.get_serving_url(self.blob.key())


# misc functions
def refresh(model_instance):
    # refeshes an instance in case things were updated since the last reference to this object (used in testing)
    return db.get(model_instance.key())

def stripHTML(string):
    return re.sub(r'<[^<]*?/?>', '', string)

# based on formencode.validators.URL.url_re, with slight modifications
URL_RE = re.compile(r'''
        ((http|https)://
        (?:[%:\w]*@)?                                               # authenticator
        (?P<domain>[a-z0-9][a-z0-9\-]{1,62}\.)*                     # (sub)domain - alpha followed by 62max chars (63 total)
        (?P<tld>[a-z]{2,})                                          # TLD
        (?::[0-9]+)?                                                # port
        (?P<path>/[a-z0-9\-\._~:/\?#\[\]@!%\$&\'\(\)\*\+,;=]*)?)    # files/delims/etc
    ''', re.I | re.VERBOSE)

def linkURLs(string):
    return URL_RE.sub(r'<a href="\1" target="_blank">\1</a>', string)

def makePostSlug(title, blog, post=None):
    """ creates a slug for use in a url """
    slug = title.lower().replace(" ", "-").replace("---", "-")[:500].encode("utf-8")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    existing = blog.posts.filter("slug =", slug).get()
    if (not post and existing) or ((post and existing) and post.key() != existing.key()):
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = blog.posts.filter("slug =", new_slug).get()
            if not existing:
                slug = new_slug
    return slug

def makeAuthorSlug(name, blog, author=None):
    """ creates a slug for use in a url """
    slug = name.lower().replace(" ", "-").replace("---", "-")[:500].encode("utf-8")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    existing = blog.authors.filter("slug =", slug).get()
    if (not author and existing) or ((author and existing) and author.key() != existing.key()):
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = blog.authors.filter("slug =", new_slug).get()
            if not existing:
                slug = new_slug
    return slug

def checkImageName(name):
    """ make sure the file name is a supported image type """
    name = name.lower()

    if not name or "." not in name:
        return None

    filename, ext = name.rsplit('.')
    if ext not in ['jpg', 'jpeg', 'gif', 'png']:
        # bad file extension
        return None

    return name

