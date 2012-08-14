# this is the main entry point for the application

import os
import sys
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

# url routes
BLOG_URLS = ['/blog']

from controllers import admin, author, contact, feed, index, post

ROUTES = []

for url in BLOG_URLS:
    ROUTES.extend([(url, index.IndexController),
                   (url + '/feed', feed.FeedController),
                   (url + '/contact/(.*)', contact.ContactController),
                   (url + '/post/(.*)', post.PostController),
                   (url + '/author/(.*)', author.AuthorController),
                   (url + '/admin', admin.AdminController),
                   (url + '/admin/blog', admin.BlogController),
                   (url + '/admin/author/(.*)', admin.AuthorController),
                   (url + '/admin/authors', admin.AuthorsController),
                   (url + '/admin/post/(.*)', admin.PostController),
                   (url + '/admin/posts', admin.PostsController),
                   (url + '/admin/preview/(.*)', admin.PreviewController),
                   (url + '/admin/comments', admin.CommentsController),
                   (url + '/admin/image', admin.ImageController),
                   (url + '/admin/images', admin.ImagesController)
                ])

def main():
    app = application()
    util.run_wsgi_app(app)

def application():
    return webapp.WSGIApplication(ROUTES, debug=True)

if __name__ == "__main__":
    main()

