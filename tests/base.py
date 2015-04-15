
import base64
import os
import pickle
import unittest

from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

from config import BLOG_PATH

import model

UCHAR = u"\u03B4" # lowercase delta


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        # Next, declare which service stubs you want to use.
        self.testbed.init_blobstore_stub()
        self.testbed.init_files_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        # need to include the path where queue.yaml exists so that the stub knows about named queues
        self.testbed.init_taskqueue_stub(root_path=BLOG_PATH)
        self.task_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def executeDeferred(self, name="default"):
        # see http://stackoverflow.com/questions/6632809/gae-unit-testing-taskqueue-with-testbed
        tasks = self.task_stub.GetTasks(name)
        self.task_stub.FlushQueue(name)
        while tasks:
            for task in tasks:
                (func, args, opts) = pickle.loads(base64.b64decode(task["body"]))
                func(*args)
            tasks = self.task_stub.GetTasks(name)
            self.task_stub.FlushQueue(name)

        # Run each of the tasks, checking that they succeeded.
        for task in tasks:
            response = self.post(task['url'], task['params'])
            self.assertOK(response)

    # fixtures
    def createBlog(self, url='blog'):
        title = 'Blog' + UCHAR
        self.blog = model.Blog(id=url, title=title)
        self.blog.put()
        return self.blog

    def createAuthor(self, slug='test-author', blog=None):
        if not blog:
            if hasattr(self, 'blog'):
                blog = self.blog
            else:
                blog = self.blog = self.createBlog()

        name = 'Test Author' + UCHAR
        url = 'http://www.example.com/test-author'
        email = 'test.author' + UCHAR + '@example.com'
        self.author = model.BlogAuthor(id=slug, name=name, url=url, email=email, parent=blog.key)
        self.author.put()
        return self.author

    def createTag(self, slug='test-tag', blog=None):
        if not blog:
            if hasattr(self, 'blog'):
                blog = self.blog
            else:
                blog = self.blog = self.createBlog()

        name = 'Test Tag' + UCHAR
        self.tag = model.BlogTag(id=slug, name=name, parent=blog.key)
        self.tag.put()
        return self.tag

    def createPost(self, slug='test-post', blog=None, author=None, tags=None):
        if not author:
            if hasattr(self, 'author'):
                author = self.author
            else:
                author = self.author = self.createAuthor()

        if not blog:
            blog = self.blog

        tag_keys = []
        if tags:
            tag_keys = [tag.key for tag in tags]

        title = 'Test Post Title' + UCHAR
        body = ' Test Post Body' + UCHAR
        self.post = model.BlogPost(id=slug, title=title, body=body, published=True,
            author=author.key, tag_keys=tag_keys, parent=blog.key)
        self.post.put()
        return self.post

    def createComment(self, post=None):
        if not post:
            if hasattr(self, 'post'):
                post = self.post
            else:
                post = self.post = self.createPost()

        email = 'test.comment' + UCHAR + '@example.com'
        body = ' Test Comment Body' + UCHAR
        self.comment = model.BlogComment(email=email, body=body, parent=post.key)
        self.comment.put()
        return self.comment

    def createImage(self, blog=None):
        from google.appengine.api import files

        if not blog:
            if hasattr(self, 'blog'):
                blog = self.blog
            else:
                blog = self.blog = self.createBlog()

        blob = files.blobstore.create(mime_type='image/jpg')
        files.finalize(blob)
        blob_key = files.blobstore.get_blob_key(blob)

        url = 'http://www.example.com/test-image'
        self.image = model.BlogImage(blob=blob_key, url=url, parent=blog.key)
        self.image.put()
        return self.image
