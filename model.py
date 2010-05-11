
import re
from time import mktime
from datetime import datetime

from google.appengine.ext import db
from google.appengine.api import images


# standard model objects
class Blog(db.Model):

    title = db.StringProperty()
    description = db.StringProperty()
    comments = db.BooleanProperty(default=False)
    moderation_alert = db.BooleanProperty(default=False)
    contact = db.BooleanProperty(default=False)
    admin_email = db.StringProperty()
    posts_per_page = db.IntegerProperty(default=10)
    url = db.StringProperty(default='/blog')
    template = db.StringProperty()

    @property
    def published_posts(self):
        return self.posts.filter('published =', True).filter('timestamp <', datetime.utcnow()).order('-timestamp')

class BlogAuthor(db.Model):

    name = db.StringProperty(required=True)
    slug = db.StringProperty(default='') # TODO: switch to required=True after uploading new version and resaving authors
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
    post = db.ReferenceProperty(BlogPost, required=True, collection_name="comments")
    author = db.ReferenceProperty(BlogAuthor, collection_name="comments")

    def __init__(self, *args, **kwargs):
        assert "email" in kwargs or "author" in kwargs, "A BlogComment needs either an email address or attached author for verification."
        return super(BlogComment, self).__init__(*args, **kwargs)

    @property
    def secondsSinceEpoch(self):
        return mktime(self.timestamp.timetuple())

class BlogImage(db.Model):

    name = db.StringProperty(required=True)
    preview = db.BlobProperty() # a smaller version of the full image
    timestamp = db.DateTimeProperty(auto_now_add=True)
    blog = db.ReferenceProperty(Blog, required=True, collection_name="images")

    @property
    def data(self):
        # reconstruct all the data for viewing
        return ''.join([image_data.data for image_data in self.image_datas])

    def setData(self, bits):
        # image data is added as other data entities dynamically, as needed

        split_bits = []
        if bits:
            # create the preview image
            # NOTE: should this preview size be configurable?
            # TODO: disabled until GAE fixes the limitation on resizing large images
            #self.preview = db.Blob(images.resize(bits, 600, 600))

            # cut it up into less than 1 MB chunks as necessary
            mb = 1048000 # needs to be less than an actual MB (2**20) to account for other data like the reference
            while len(bits) > mb:
                chunk = bits[:mb]
                split_bits.append(chunk)
                bits = bits[mb:]
            if bits:
                # finally, add any leftover fraction that's less than 1 MB
                split_bits.append(bits)

        if split_bits:
            # delete any pre-existing references
            if self.image_datas.count() > 0:
                db.delete(self.image_datas)

            # add new stuff in
            for d in split_bits:
                image_data = BlogImageData(data=d, image=self)
                image_data.put()

class BlogImageData(db.Model):
    # right now GAE limits not only Blobs to 1 MB, but entities as well
    # so we create a collection of entities to store an image that's over that size
    data = db.BlobProperty(required=True)
    image = db.ReferenceProperty(BlogImage, required=True, collection_name="image_datas")


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
    slug = title.lower().replace(" ", "-")
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
    slug = name.lower().replace(" ", "-")
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

def checkImageName(name, blog, image=None):
    """ make sure an image file name is unique and ok for use in a url """
    name = name.lower().replace(" ", "_")
    name = ''.join([char for char in name if char.isalnum() or char in ['-', '_', '.']])

    if not name:
        return None

    filename, ext = name.rsplit('.')
    if ext not in ['jpg', 'jpeg', 'gif', 'png']:
        # bad file extension
        return None

    existing = blog.images.filter("name =", name).get()
    if not name or (not image and existing) or ((image and existing) and image.key() != existing.key()):
        # already exists
        return None

    return name

