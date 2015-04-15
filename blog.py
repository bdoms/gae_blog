# this is the main entry point for the application

import os
import sys

import webapp2

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from gae_blog.controllers import admin, author, contact, error, feed, index, pingback, post, tag, trackback, verify, webmention

# url routes
BLOG_URLS = ['/blog']

ROUTES = []

for url in BLOG_URLS:
    ROUTES.extend([(url, index.IndexController),
                   (url + '/feed', feed.FeedController),
                   (url + '/contact', contact.ContactController),
                   (url + '/post/(.[^/]+)', post.PostController),
                   (url + '/tag/(.[^/]+)', tag.TagController),
                   (url + '/author/(.[^/]+)', author.AuthorController),
                   (url + '/trackback/(.[^/]+)', trackback.TrackbackController),
                   (url + '/pingback', pingback.PingbackController),
                   (url + '/webmention', webmention.WebmentionController),
                   (url + '/verify', verify.VerifyController),
                   (url + '/admin', admin.AdminController),
                   (url + '/admin/blog', admin.BlogController),
                   (url + '/admin/author/(.*)', admin.AuthorController),
                   (url + '/admin/authors', admin.AuthorsController),
                   (url + '/admin/post/(.*)', admin.PostController),
                   (url + '/admin/posts', admin.PostsController),
                   (url + '/admin/preview/(.[^/]+)', admin.PreviewController),
                   (url + '/admin/comments', admin.CommentsController),
                   (url + '/admin/image', admin.ImageController),
                   (url + '/admin/images', admin.ImagesController),
                   (url + '/admin/migrate', admin.MigrateController),
                   (url + '/(.*)', error.ErrorController)
                ])

# any extra config needed when the app starts
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'replace this with the output from os.urandom(64)',
    'cookie_args': {
        # uncomment this line to force cookies to only be sent over SSL
        #'secure': True,

        # this can prevent XSS attacks by not letting javascript access the cookie
        # (note that some older browsers do not have this restriction implemented)
        # disable if you need to access cookies from javascript (not recommended)
        'httponly': True
    }
}

app = webapp2.WSGIApplication(ROUTES, config=config, debug=False)
