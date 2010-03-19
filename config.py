# this is the place for all the application configuration constants

# templates
import os

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIR)


# url routes
BLOG_URL = '/blog'

from controllers import admin, index, post

ROUTES = [(BLOG_URL, index.IndexController),
          (BLOG_URL + '/post/(.*)', post.PostController),
          (BLOG_URL + '/admin', admin.AdminController),
          (BLOG_URL + '/admin/post/(.*)', admin.PostController),
          (BLOG_URL + '/admin/posts', admin.PostsController),
          (BLOG_URL + '/admin/comments', admin.CommentsController)
         ]
