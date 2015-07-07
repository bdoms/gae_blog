
import re
from time import mktime
from datetime import datetime

from google.appengine.ext import ndb


# standard model objects
class Blog(ndb.Model):

    title = ndb.StringProperty()
    description = ndb.StringProperty()
    enable_comments = ndb.BooleanProperty(default=False)
    enable_linkbacks = ndb.BooleanProperty(default=False)
    moderation_alert = ndb.BooleanProperty(default=False)
    contact = ndb.BooleanProperty(default=False)
    author_pages = ndb.BooleanProperty(default=False)
    admin_email = ndb.StringProperty()
    posts_per_page = ndb.IntegerProperty(default=10)
    image_preview_size = ndb.IntegerProperty(default=600)
    template = ndb.StringProperty()
    mail_queue = ndb.StringProperty(default="mail")
    blocklist = ndb.StringProperty(repeated=True)

    @property
    def slug(self):
        return self.key.string_id()

    @property
    def posts(self):
        return BlogPost.query(ancestor=self.key)

    @property
    def authors(self):
        return BlogAuthor.query(ancestor=self.key)

    @property
    def comments(self):
        return BlogComment.query(ancestor=self.key)

    @property
    def images(self):
        return BlogImage.query(ancestor=self.key)

    @property
    def children(self):
        # comments are grand children, not direct children, so they are not included here
        return list(self.posts) + list(self.authors) + list(self.images)

    @property
    def published_posts(self):
        return self.posts.filter(BlogPost.published == True).filter(BlogPost.timestamp < datetime.utcnow()).order(-BlogPost.timestamp)


class BlogAuthor(ndb.Model):

    name = ndb.StringProperty(required=True)
    url = ndb.StringProperty()
    email = ndb.StringProperty()

    @property
    def slug(self):
        return self.key.string_id()

    @property
    def blog(self):
        return self.key.parent().get()

    @property
    def comments(self):
        return BlogComment.query(BlogComment.author == self.key)

    @property
    def posts(self):
        return BlogPost.query(BlogPost.author == self.key)

    @property
    def published_posts(self):
        return self.posts.filter(BlogPost.published == True).filter(BlogPost.timestamp < datetime.utcnow()).order(-BlogPost.timestamp)


class BlogTag(ndb.Model):

    name = ndb.StringProperty(required=True)

    @property
    def slug(self):
        return self.key.string_id()

    @property
    def blog(self):
        return self.key.parent().get()

    @property
    def posts(self):
        return BlogPost.query(BlogPost.tag_keys == self.key)

    @property
    def published_posts(self):
        return self.posts.filter(BlogPost.published == True).filter(BlogPost.timestamp < datetime.utcnow()).order(-BlogPost.timestamp)


class BlogPost(ndb.Model):

    title = ndb.StringProperty(required=True) # max of 500 chars
    body = ndb.TextProperty() # returns type db.Text (a subclass of unicode)
    published = ndb.BooleanProperty(default=False)
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    author = ndb.KeyProperty(kind=BlogAuthor, required=True)
    tag_keys = ndb.KeyProperty(kind=BlogTag, repeated=True)

    @property
    def slug(self):
        return self.key.string_id()

    @property
    def blog(self):
        return self.key.parent().get()

    @property
    def tags(self):
        return ndb.get_multi(self.tag_keys)

    @property
    def tag_names(self):
        return [tag.name for tag in self.tags]

    @property
    def comments(self):
        return BlogComment.query(ancestor=self.key)

    @property
    def approved_comments(self):
        return self.comments.filter(BlogComment.approved == True).order(BlogComment.timestamp)

    @property
    def approved_user_comments(self):
        return [comment for comment in self.approved_comments if not comment.linkback]

    @property
    def approved_linkbacks(self):
        return [comment for comment in self.approved_comments if comment.linkback]

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

    def enabled_comments(self, blog):
        comments = []
        if blog.enable_comments and blog.enable_linkbacks:
            comments = list(self.approved_comments)
        elif blog.enable_comments:
            comments = self.approved_user_comments
        elif blog.enable_linkbacks:
            comments = self.approved_linkbacks
        return comments


class BlogComment(ndb.Model):

    name = ndb.StringProperty()
    url = ndb.StringProperty()
    email = ndb.StringProperty()
    body = ndb.TextProperty()
    blog_name = ndb.StringProperty()
    trackback = ndb.BooleanProperty(default=False)
    pingback = ndb.BooleanProperty(default=False)
    webmention = ndb.BooleanProperty(default=False)
    approved = ndb.BooleanProperty(default=False)
    timestamp = ndb.DateTimeProperty(auto_now_add=True)
    ip_address = ndb.StringProperty(default='')
    author = ndb.KeyProperty(kind=BlogAuthor)

    @property
    def post(self):
        return self.key.parent().get()

    @property
    def secondsSinceEpoch(self):
        return mktime(self.timestamp.timetuple())

    @property
    def linkback(self):
        return self.trackback or self.pingback or self.webmention


class BlogImage(ndb.Model):

    blob = ndb.BlobKeyProperty(required=True)
    timestamp = ndb.DateTimeProperty(auto_now_add=True) # this information is also on the blob, but having it here makes it possible to order by
    url = ndb.StringProperty(default="")

    @property
    def blog(self):
        return self.key.parent().get()


# misc functions
def stripHTML(string):
    # remove style or script tags first, and that includes anything inside them
    some_html = re.sub(r'(<style>.*</style>)*(<script>.*</script>)*', '', string)
    # now remove all other tags, but keep their inner content intact
    return re.sub(r'<[^<]*?/?>', '', some_html)

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


def makeNew(model_object, id=None, parent=None, use_transaction=True):
    """ if a key name or parent changes then the key does - since it's immutable per object we must recreate it entirely """
    def newTransaction():
        # get old info
        d = model_object.to_dict()
        # list forces execution, which we need since we're about to delete this
        children = hasattr(model_object, "children") and list(model_object.children) or []
        # delete current (must come first so that the key name can be made the same if necessary)
        model_object.key.delete()
        # make new
        new_object = model_object.__class__(id=id, parent=parent, **d)
        new_object.put()

        # replace the parent on all the children
        # NOTE that nested transactions aren't supported, so these must use_transaction=False
        for child in children:
            child_name = hasattr(child, "slug") and child.slug or None
            new_child = makeNew(child, id=child_name, parent=new_object.key, use_transaction=False)

        return new_object

    if use_transaction:
        new_object = ndb.transaction(newTransaction)
    else:
        new_object = newTransaction()

    return new_object

def slugify(name):
    slug = name.lower().replace(" ", "-").replace("/", "-").encode("utf-8")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    slug = re.sub(r'(-)\1+', '-', slug)
    if slug.endswith('-'): slug = slug[:-1]
    return slug[:500]

def makeSlug(name, blog, model_class, entity=None):
    """ creates a slug for use in a url """
    slug = slugify(name)
    existing = model_class.get_by_id(slug, parent=blog.key)
    if (not entity and existing) or ((entity and existing) and entity.key != existing.key):
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = model_class.get_by_id(new_slug, parent=blog.key)
            if not existing:
                slug = new_slug
    return slug

def checkImageName(name):
    """ make sure the file name is a supported image type """
    name = name.lower()

    if not name or "." not in name:
        return None

    filename, ext = name.rsplit('.', 1)
    if ext not in ['jpg', 'jpeg', 'gif', 'png']:
        # bad file extension
        return None

    return name
