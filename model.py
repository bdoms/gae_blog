
from google.appengine.ext import db


# standard model objects
class BlogGlobal(db.Model):

    title = db.StringProperty(required=True)
    comments = db.BooleanProperty(required=True)

class BlogPost(db.Model):

    title = db.StringProperty(required=True) # max of 500 chars
    slug = db.StringProperty(required=True)
    body = db.TextProperty() # returns type db.Text (a subclass of unicode)
    published = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)

    @property
    def approved_comments(self):
        #ordered_comments = self.comments.order_by(timestamp) # TODO: this needs the correct syntax
        return [comment for comment in self.comments if comment.approved]

class BlogComment(db.Model):

    name = db.StringProperty()
    url = db.StringProperty()
    email = db.StringProperty(required=True)
    body = db.StringProperty(required=True)
    approved = db.BooleanProperty(default=False)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    post = db.ReferenceProperty(BlogPost, required=True, collection_name="comments")


# misc functions
def refresh(model_instance):
    # refeshes an instance in case things were updated since the last reference to this object (used in testing)
    return db.get(model_instance.key())



def makePostSlug(title, post=None):
    """ creates a slug for use in a url """
    slug = title.lower().replace(" ", "-")
    slug = ''.join([char for char in slug if char.isalnum() or char == '-'])
    existing = BlogPost.all().filter("slug =", slug).get()
    if post and post.key() != existing.key():
        # only work on finding a new slug if this isn't the same post that already uses it
        i = 0
        while existing:
            i += 1
            new_slug = slug + "-" + str(i)
            existing = BlogPost.all.filter("slug =", new_slug).get()
            if not existing:
                slug = new_slug
    return slug

