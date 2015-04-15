
import datetime

from base import BaseTestCase, UCHAR

import model


class TestBlogPost(BaseTestCase):

    def test_summarize(self):
        post = self.createPost()
        post.body = 'test body for summarize' + UCHAR

        full = post.summarize(5)
        assert full == post.body

        short = post.summarize(2)
        assert short == 'test body...'

    def test_enabled_comments(self):
        comment1 = self.createComment()
        comment1.approved = True
        comment1.put()
        comment2 = self.createComment()
        comment2.approved = True
        comment2.put()
        comment3 = self.createComment()
        comment3.approved = True
        comment3.trackback = True
        comment3.put()
        post = comment1.post
        blog = post.blog

        assert len(post.enabled_comments(blog)) == 0

        blog.enable_comments = True

        assert len(post.enabled_comments(blog)) == 2

        blog.enable_linkbacks = True

        assert len(post.enabled_comments(blog)) == 3

        blog.enable_comments = False

        assert len(post.enabled_comments(blog)) == 1


class TestModelFunctions(BaseTestCase):

    def test_stripHTML(self):
        html = '<script>alert("hi");</script> <p>test</p>'
        stripped = model.stripHTML(html)

        assert stripped == ' test'


    def test_linkURLs(self):
        links = 'text with http://www.example.com links'
        html = model.linkURLs(links)

        assert html == 'text with <a href="http://www.example.com" target="_blank">http://www.example.com</a> links'


    def test_makeNew(self):
        # create a post so that the blog has children
        post = self.createPost()
        new_blog = model.makeNew(self.blog, id='new-blog', use_transaction=False)

        assert new_blog.slug == 'new-blog'


    def test_slugify(self):
        name = 'Test Post with-&-a--lot---of----hyphens-' + UCHAR
        slug = model.slugify(name)

        assert slug == 'test-post-with-a-lot-of-hyphens'


    def test_makeSlug(self):
        # without a pre-existing entity
        blog = self.createBlog()
        name = 'Test Post' + UCHAR
        slug = model.makeSlug(name, blog, model.BlogPost)

        assert slug == 'test-post'

        # with a pre-existing entity
        post = self.createPost(blog=blog, slug='test-post-title')
        slug = model.makeSlug(post.title, blog, model.BlogPost, entity=post)

        assert slug == post.slug


    def test_checkImageName(self):
        # no extension
        name = model.checkImageName('FILE')

        assert name is None

        # unsupported extension
        name = model.checkImageName('FILE.TXT')

        assert name is None

        # supported extension (with two dots to ensure the split is correct)
        name = model.checkImageName('FILE.NAME.JPG')

        assert name == 'file.name.jpg'
