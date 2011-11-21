
import re
from time import mktime
from datetime import datetime

from google.appengine.ext import db, blobstore
from google.appengine.api import images


# standard model objects
class Blog(db.Model):

    title = db.StringProperty()
    description = db.StringProperty()
    enable_comments = db.BooleanProperty(default=False)
    moderation_alert = db.BooleanProperty(default=False)
    contact = db.BooleanProperty(default=False)
    admin_email = db.StringProperty()
    posts_per_page = db.IntegerProperty(default=10)
    image_preview_size = db.IntegerProperty(default=600)
    template = db.StringProperty()
    blocklist = db.ListProperty(str)

    @property
    def slug(self):
        return self.key().name()

    @property
    def posts(self):
        return BlogPost.all().ancestor(self)

    @property
    def authors(self):
        return BlogAuthor.all().ancestor(self)

    @property
    def comments(self):
        return BlogComment.all().ancestor(self)

    @property
    def images(self):
        return BlogImage.all().ancestor(self)

    @property
    def children(self):
        # comments are grand children, not direct children, so they are not included here
        return list(self.posts) + list(self.authors) + list(self.images)

    @property
    def published_posts(self):
        return self.posts.filter('published =', True).filter('timestamp <', datetime.utcnow()).order('-timestamp')


class BlogAuthor(db.Model):

    name = db.StringProperty(required=True)
    url = db.StringProperty()
    email = db.StringProperty()

    @property
    def slug(self):
        return self.key().name()

    @property
    def blog(self):
        return self.parent()

    @property
    def published_posts(self):
        return self.posts.filter('published =', True).filter('timestamp <', datetime.utcnow()).order('-timestamp')


class BlogPost(db.Model):

    title = db.StringProperty(required=True) # max of 500 chars
    body = db.TextProperty() # returns type db.Text (a subclass of unicode)
    published = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    author = db.ReferenceProperty(BlogAuthor, required=True, collection_name="posts")

    @property
    def slug(self):
        return self.key().name()

    @property
    def blog(self):
        return self.parent()

    @property
    def comments(self):
        return BlogComment.all().ancestor(self)

    @property
    def approved_comments(self):
        return self.comments.filter('approved =', True).order('timestamp')

    @property
    def children(self):
        return self.comments

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
    author = db.ReferenceProperty(BlogAuthor, collection_name="comments")

    def __init__(self, *args, **kwargs):
        assert "email" in kwargs or "author" in kwargs, "A BlogComment needs either an email address or attached author for verification."
        return super(BlogComment, self).__init__(*args, **kwargs)

    @property
    def post(self):
        return self.parent()

    @property
    def secondsSinceEpoch(self):
        return mktime(self.timestamp.timetuple())


class BlogImage(db.Model):

    blob = blobstore.BlobReferenceProperty(required=True)

    @property
    def blog(self):
        return self.parent()

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


# model helper functions
def toDict(model_object):
    """ convert a model object to a dictionary """
    d = {}
    for prop in model_object.properties():
        # we must avoid de-referencing the values for the reference properties in case this is run in a transaction
        if type(getattr(model_object.__class__, prop)) == db.ReferenceProperty:
            d[prop] = getattr(model_object.__class__, prop).get_value_for_datastore(model_object)
        else:
            d[prop] = getattr(model_object, prop)
    return d

def makeNew(model_object, key_name=None, parent=None, use_transaction=True):
    """ if a key name or parent changes then the key does - since it's immutable per object we must recreate it entirely """
    def transaction(model_object, key_name=key_name, parent=None):
        # get old info
        d = toDict(model_object)
        # list forces execution, which we need since we're about to delete this
        children = hasattr(model_object, "children") and list(model_object.children) or []
        # delete current (must come first so that the key name can be made the same if necessary)
        model_object.delete()
        # make new
        new_object = model_object.__class__(key_name=key_name, parent=parent, **d)
        new_object.put()

        # replace the parent on all the children
        # NOTE that nested transactions aren't supported, so these must use_transaction=False
        for child in children:
            child_name = hasattr(child, "slug") and child.slug or None
            new_child = makeNew(child, key_name=child_name, parent=new_object, use_transaction=False)

        return new_object

    if use_transaction:
        new_object = db.run_in_transaction(transaction, model_object, key_name=key_name, parent=parent)
    else:
        new_object = transaction(model_object, key_name=key_name, parent=parent)

    return new_object

def makePostSlug(title, blog, post=None):
    """ creates a slug for use in a url """
    slug = title.lower().replace(" ", "-").replace("---", "-")[:500].encode("utf-8")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    existing = BlogPost.get_by_key_name(slug, parent=blog)
    if (not post and existing) or ((post and existing) and post.key() != existing.key()):
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = BlogPost.get_by_key_name(new_slug, parent=blog)
            if not existing:
                slug = new_slug
    return slug

def makeAuthorSlug(name, blog, author=None):
    """ creates a slug for use in a url """
    slug = name.lower().replace(" ", "-").replace("---", "-")[:500].encode("utf-8")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    existing = BlogAuthor.get_by_key_name(slug, parent=blog)
    if (not author and existing) or ((author and existing) and author.key() != existing.key()):
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = BlogAuthor.get_by_key_name(new_slug, parent=blog)
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

