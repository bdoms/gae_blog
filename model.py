
import re
from time import mktime

from google.appengine.ext import db


# standard model objects
class Blog(db.Model):

    title = db.StringProperty()
    description = db.StringProperty()
    comments = db.BooleanProperty(required=True)
    url = db.StringProperty(default='/blog')
    template = db.StringProperty()

    @property
    def published_posts(self):
        return self.posts.filter('published =', True).order('timestamp')

class BlogAuthor(db.Model):

    name = db.StringProperty(required=True)
    blog = db.ReferenceProperty(Blog, required=True, collection_name="authors")

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
        no_html = re.sub(r'<[^<]*?/?>', '', self.body)
        words = no_html.split(" ")
        if len(words) <= length:
            return no_html
        else:
            return " ".join(words[:length]) + "..."

class BlogComment(db.Model):

    name = db.StringProperty()
    url = db.StringProperty()
    email = db.StringProperty(required=True)
    body = db.StringProperty(required=True)
    approved = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    post = db.ReferenceProperty(BlogPost, required=True, collection_name="comments")

    @property
    def secondsSinceEpoch(self):
        return mktime(self.timestamp.timetuple())


# misc functions
def refresh(model_instance):
    # refeshes an instance in case things were updated since the last reference to this object (used in testing)
    return db.get(model_instance.key())



def makePostSlug(title, post=None):
    """ creates a slug for use in a url """
    slug = title.lower().replace(" ", "-")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    existing = BlogPost.all().filter("slug =", slug).get()
    if (post and existing) and post.key() != existing.key():
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = BlogPost.all.filter("slug =", new_slug).get()
            if not existing:
                slug = new_slug
    return slug

