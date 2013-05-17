# this is the main entry point for the application

import os
import sys

import webapp2

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.append(PARENT_DIR)

from gae_blog.controllers import admin, author, contact, error, feed, index, post

# url routes
BLOG_URLS = ['/blog']

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
                   (url + '/admin/images', admin.ImagesController),
                   (url + '/(.*)', error.ErrorController)
                ])

app = webapp2.WSGIApplication(ROUTES, debug=True)
