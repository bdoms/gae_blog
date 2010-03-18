# this is the place for all the application configuration constants

# templates
import os

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIR)


# url routes
from controllers import admin, index, post

BASE_URL = '/blog'

ROUTES = [(BASE_URL, index.IndexController),
          (BASE_URL + '/post/(.*)', post.PostController),
          (BASE_URL + '/admin', admin.AdminController),
          (BASE_URL + '/admin/post/(.*)', admin.PostController),
          (BASE_URL + '/admin/posts', admin.PostsController),
          (BASE_URL + '/admin/comments', admin.CommentsController)
         ]
