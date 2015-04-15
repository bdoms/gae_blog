import datetime
import logging
import os
import xmlrpclib

import jinja2

from google.appengine.api import memcache

from webtest import TestApp

from controllers import base as controller_base
from controllers import admin as controller_admin

from base import BaseTestCase, UCHAR, model


class BaseTestController(BaseTestCase):

    def setUp(self):
        super(BaseTestController, self).setUp()
        # this must be imported after the above setup in order for the stubs to work
        from blog import app, BLOG_URLS

        # override test app so that we can get pages relative to the blog url
        class BlogTestApp(TestApp):
            blog_url = BLOG_URLS[0]
            def get(self, url, *args, **kwargs):
                if not url.startswith('http'):
                    url = self.blog_url + url
                return super(BlogTestApp, self).get(url, *args, **kwargs)
            def post(self, url, *args, **kwargs):
                if not url.startswith('http'):
                    url = self.blog_url + url
                return super(BlogTestApp, self).post(url, *args, **kwargs)
            def request(self, url, *args, **kwargs):
                if not url.startswith('http'):
                    url = self.blog_url + url
                return super(BlogTestApp, self).request(url, *args, **kwargs)

        self.app = BlogTestApp(app)

    def setCookie(self, response):
        if 'Set-Cookie' in response.headers:
            cookies = response.headers.getall('Set-Cookie')
            os.environ['HTTP_COOKIE'] = " ".join(cookies)

    def sessionGet(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        response = self.app.get(*args, **kwargs)
        self.setCookie(response)
        return response

    def sessionPost(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        response = self.app.post(*args, **kwargs)
        self.setCookie(response)
        return response

    def login(self, is_admin=False):
        os.environ['USER_EMAIL'] ='test@example.com'
        os.environ['USER_ID'] = '1'
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    def getVerifyToken(self, path):
        # some requests need a verification token so this test isn't considered a bot
        data = {"url": "http://localhost/blog" + path}
        headers = [("referer", "http://localhost")]
        response = self.app.get('/verify', data, headers=headers)
        response = str(response)
        start = response.find('{"token": "')
        token = response[start + 11:-2] # ends with "}
        return token


class BaseMockController(BaseTestController):
    """ abstract base class for tests that need request, response, and session mocking """

    def getMockRequest(self):
        # calling straight into the controller without a route requires some mock objects to work
        class MockRequest(self.app.app.request_class):
            class MockRoute(object):
                handler_method = "get"
            app = self.app.app
            path = url = "/test-path"
            host_url = "http://localhost"
            query_string = "test=query"
            headers = route_args = route_kwargs = {}
            route = MockRoute()
        return MockRequest({})

    def mockSessions(self):
        # this is used by tests that want to bypass needing to perform session-dependent actions within a request
        class MockSessionStore(object):
            def get_session(self): return {}
        self.controller.session_store = MockSessionStore()


class TestBase(BaseMockController):

    def setUp(self):
        super(TestBase, self).setUp()

        self.controller = controller_base.BaseController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

    def test_dispatch(self):

        self.called = False
        def get(): self.called = True
        self.controller.get = get

        self.controller.dispatch()

        assert self.called

    def test_session(self):
        # sessions can only be used during a request, so we create a mock one to save something
        def get(): self.controller.session["test key"] = "test value" + UCHAR
        self.controller.get = get
        self.controller.dispatch()
        assert self.controller.session.get("test key") == "test value" + UCHAR

    def test_compileTemplate(self):
        self.mockSessions()
        template = jinja2.Template("test compile template" + UCHAR)
        result = self.controller.compileTemplate(template)
        assert "test compile template" + UCHAR in result

    def test_renderTemplate(self):
        self.mockSessions()
        template = jinja2.Template("test render template" + UCHAR)
        self.controller.renderTemplate(template)
        assert self.controller.response.headers['Content-Type'] == "text/html; charset=utf-8"
        assert "test render template" + UCHAR in self.controller.response.unicode_body

    def test_renderError(self):
        self.mockSessions()
        self.controller.renderError(500)
        assert "Error 500:" in self.controller.response.body

    def test_renderJSON(self):
        self.controller.renderJSON({"test key": "test value" + UCHAR})
        assert self.controller.response.headers['Content-Type'] == "application/json; charset=utf-8"
        assert self.controller.response.unicode_body == '{"test key": "test value' + UCHAR + '"}'

    def test_head(self):
        def get(): self.called = True
        self.controller.get = get

        # HEAD should just call the GET version
        self.called = False
        self.controller.head()
        assert self.called

        # but not have a response body
        assert not self.controller.response.unicode_body
        assert not self.controller.response.body

    def test_handle_exception(self):
        self.mockSessions()
        # temporarily disable exception logging for this test to avoid messy printouts
        logging.disable(logging.CRITICAL)
        self.controller.handle_exception("test exception", False)
        logging.disable(logging.NOTSET)
        assert "Error 500:" in self.controller.response.body

    def test_user(self):
        assert self.controller.user is None

        self.login()

        # re-init to clear old response
        self.controller = controller_base.BaseController()

        assert self.controller.user is not None

    def test_user_is_admin(self):
        assert not self.controller.user_is_admin

        self.login(is_admin=True)

        # re-init to clear old response
        self.controller = controller_base.BaseController()

        assert self.controller.user_is_admin

    def test_blog(self):
        assert self.controller.blog is None

        self.createBlog(url='test-path')

        # re-init to clear old response
        self.controller = controller_base.BaseController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

        assert self.controller.blog is not None

    def test_blog_slug(self):
        assert self.controller.blog_slug == 'test-path'

    def test_blog_url(self):
        assert self.controller.blog_url == '/test-path'

    def test_errorsFromSession(self):
        self.mockSessions()
        form_data, errors = self.controller.errorsFromSession()
        assert form_data == {}
        assert errors == {}

    def test_sendEmail(self):
        sender = "sender" + UCHAR + "@example.com"
        to = "test" + UCHAR + "@example.com"
        subject = "Subject" + UCHAR
        body = "Test body"
        self.controller.sendEmail(sender, to, subject, body)

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == to
        assert messages[0].subject == subject
        assert body in str(messages[0].body)
        assert not hasattr(messages[0], "reply_to")

        reply_to = "test_reply" + UCHAR + "@example.com"
        self.controller.sendEmail(sender, to, subject, body, reply_to)
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 2
        assert messages[1].reply_to == reply_to

    def test_deferEmail(self):
        blog = self.createBlog()
        blog.admin_email = "test.admin" + UCHAR + "@example.com"
        self.controller.blog = blog

        to = "test" + UCHAR + "@example.com"
        subject = "Subject" + UCHAR
        body = "Test body"
        self.controller.deferEmail(to, subject, body)

        # move mails out of the queue so we can test them
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == to
        assert messages[0].subject == subject
        assert body in str(messages[0].body)

    def test_linkbackEmail(self):
        blog = self.createBlog()
        post = self.createPost(blog=blog)
        comment = self.createComment(post=post)
        self.controller.blog = blog

        # no moderation alert
        self.controller.linkbackEmail(post, comment)

        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 0

        # no admin email
        self.controller.blog.moderation_alert = True

        self.controller.linkbackEmail(post, comment)

        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 0

        # success
        self.controller.blog.admin_email = "test.admin" + UCHAR + "@example.com"

        self.controller.linkbackEmail(post, comment)

        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert "Comment Awaiting Moderation" in messages[0].subject


class TestForm(BaseMockController):

    class UnicodeMockRequest(object):
        path = url = "/test-path"
        method = "POST"
        def __init__(self, d):
            self.d = d
        def get(self, field):
            value = self.d.get(field)
            if value:
                value = unicode(value)
            return value

    def setUp(self):
        super(TestForm, self).setUp()

        self.controller = controller_base.FormController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

    def test_validate(self):
        self.controller.request = {"valid_field": "value" + UCHAR, "invalid_field": "value" + UCHAR}
        self.controller.FIELDS = {"valid_field": lambda x: (True, x + "valid"), "invalid_field": lambda x: (False, "")}
        form_data, errors, valid_data = self.controller.validate()

        assert form_data == self.controller.request
        assert errors == {"invalid_field": True}
        assert valid_data == {"valid_field": "value" + UCHAR + "valid"}

        # non-utf8 should result in a bad request
        self.mockSessions()
        self.controller.request = self.UnicodeMockRequest({"valid_field": "\xff"})
        self.controller.validate()
        assert self.controller.response.status_int == 400

    def test_redisplay(self):
        self.mockSessions()

        self.controller.redisplay("form_data", "errors", "/test-redirect-url")

        assert self.controller.session.get("form_data") == "form_data"
        assert self.controller.session.get("errors") == "errors"

        assert self.controller.response.status_int == 302
        assert "Location: /test-redirect-url" in str(self.controller.response.headers)

    def test_botProtection(self):
        # non-utf8 should result in a bad request
        self.controller.request = self.UnicodeMockRequest({"token": "\xff"})

        path = "/test-redirect"
        full_path = self.UnicodeMockRequest.path + path
        bot = self.controller.botProtection(path)

        assert bot
        assert self.controller.response.status_int == 400

        # re-init to clear old response
        self.controller = controller_base.FormController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

        # something in the honeypot should cause a silent failure
        self.controller.request = self.UnicodeMockRequest({"honeypot": "anything"})

        bot = self.controller.botProtection(path)

        assert bot
        assert self.controller.response.status_int == 302
        assert "Location: " + full_path in str(self.controller.response.headers)

        # re-init to clear old response
        self.controller = controller_base.FormController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

        # invalid token should cause a silent failure
        self.controller.request = self.UnicodeMockRequest({"token": "not valid"})

        bot = self.controller.botProtection(path)

        assert bot
        assert self.controller.response.status_int == 302
        assert "Location: " + full_path in str(self.controller.response.headers)

        # re-init to clear old response
        self.controller = controller_base.FormController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

        # valid token should pass
        token = self.controller.generateToken(self.UnicodeMockRequest.path)
        self.controller.request = self.UnicodeMockRequest({"token": token})

        bot = self.controller.botProtection("")

        assert not bot

    def test_generateToken(self):
        salt = "static salt for testing generateToken"
        memcache.set(self.controller.SALT_KEY, salt)
        dt = datetime.datetime(2000, 1, 1)

        result = self.controller.generateToken("/blog/test-path", timestamp=dt)
        
        assert result == "4a4659bd137f6296ac850e4b57aef19e49ec98a2e3d8dfb518a8900c24765fbc256ddc0991d4cb33a540453d3a9a5d3c574fd91e0b991366c923c48824a602a5"


class TestError(BaseTestController):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        assert self.app.get('/nothing-to-see-here', status=404)


class TestAuthor(BaseTestController):

    def test_author(self):
        # no blog
        assert self.app.get('/author/nothing', status=403)

        blog = self.createBlog()
        blog.enable_comments = True

        # author pages not enabled
        assert self.app.get('/author/nothing', status=403)

        blog.author_pages = True

        # no author
        assert self.app.get('/author/nothing', status=404)

        author = self.createAuthor(blog=blog)
        
        response = self.app.get('/author/' + author.slug)
        assert "Author - " + author.name in response
        assert "No posts yet." in response

        post = self.createPost()
        response = self.app.get('/author/' + author.slug)
        assert post.body in response

        # test that ordering works correctly
        post2 = self.createPost(slug='second-test-post')
        response = self.app.get('/author/' + author.slug)
        assert unicode(response).index(post2.slug) < unicode(response).index(post.slug)

        # and can be flipped
        response = self.app.get('/author/' + author.slug + '?order=asc')
        assert unicode(response).index(post2.slug) > unicode(response).index(post.slug)


class TestTag(BaseTestController):

    def test_tag(self):
        # no blog
        assert self.app.get('/tag/nothing', status=403)

        blog = self.createBlog()

        # no tag
        assert self.app.get('/tag/nothing', status=404)

        tag = self.createTag(blog=blog)
        
        response = self.app.get('/tag/' + tag.slug)
        assert "Tag - " + tag.name in response
        assert "No posts yet." in response

        post = self.createPost(tags=[tag])
        response = self.app.get('/tag/' + tag.slug)
        assert post.body in response

        # test that ordering works correctly
        post2 = self.createPost(slug='second-test-post', tags=[tag])
        response = self.app.get('/tag/' + tag.slug)
        assert unicode(response).index(post2.slug) < unicode(response).index(post.slug)

        # and can be flipped
        response = self.app.get('/tag/' + tag.slug + '?order=asc')
        assert unicode(response).index(post2.slug) > unicode(response).index(post.slug)


class TestContact(BaseTestController):

    def test_contact(self):
        # no blog
        assert self.app.get('/contact', status=403)

        blog = self.createBlog()

        # contact page not enabled
        assert self.app.get('/contact', status=403)

        blog.contact = True

        # no admin email
        response = self.app.get('/contact')
        assert "<h3>Contact</h3>" in response
        assert "There is no admin email address for this blog" in response

        blog.admin_email = "test.admin" + UCHAR + "@example.com"

        # no authors
        response = self.app.get('/contact')
        assert "<h3>Contact</h3>" in response
        assert "There aren't any authors for this blog yet." in response

        author = self.createAuthor(blog=blog)
        email = author.email
        author.email = ''

        response = self.app.get('/contact')
        assert "There aren't any emails associated with authors yet." in response

        author.email = email
        response = self.app.get('/contact')
        assert "(required for verification)" in response

    def test_sendContact(self):
        # no blog
        assert self.app.post('/contact', status=403)

        blog = self.createBlog()

        # contact page not enabled
        assert self.app.post('/contact', status=403)

        blog.contact = True

        # no admin email
        assert self.app.post('/contact', status=403)

        blog.admin_email = "test.admin" + UCHAR + "@example.com"

        author = self.createAuthor(blog=blog)

        data = {}
        data["author"] = author.slug
        data["email"] = "test.contact" + UCHAR + "@example.com"
        data["subject"] = ("Test Contact Subject" + UCHAR).encode("utf-8")
        data["body"] = "Test Contact Body" + UCHAR
        data["token"] = self.getVerifyToken('/contact')

        response = self.app.post('/contact', data)
        response = response.follow()
        assert "Message sent successfully." in response

        # and the contact email should've been sent
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert author.email in messages[0].to
        assert data["subject"] in messages[0].subject.encode("utf-8")


class TestFeed(BaseTestController):

    def test_feed(self):
        blog = self.createBlog()
        author = self.createAuthor()
        tag = self.createTag()
        self.createPost(author=author, tags=[tag])

        response = self.app.get('/feed')
        assert "<rss" in response
        assert self.blog.title in response
        assert self.post.title in response
        assert "<category>" + tag.name + "</category>" in response

        response = self.app.get('/feed?author=' + author.slug)
        assert "Author - " + author.name not in response

        blog.author_pages = True

        response = self.app.get('/feed?author=' + author.slug)
        assert "Author - " + author.name in response

        response = self.app.get('/feed?tag=' + tag.slug)
        assert "Tag - " + tag.name in response


class TestIndex(BaseTestController):

    def test_index(self):
        response = self.app.get('')
        assert "There's nothing here yet." in response

        blog = self.createBlog(url='blog')
        blog.enable_comments = True
        response = self.app.get('')
        assert "No posts yet." in response

        post = self.createPost()
        response = self.app.get('')
        assert post.body in response


class TestPost(BaseTestController):

    def test_post_headers(self):
        # no blog
        assert self.app.get('/post/nothing', status=404)

        blog = self.createBlog()

        # no post
        assert self.app.get('/post/nothing', status=404)

        post = self.createPost()
        response = self.app.get('/post/' + post.slug)
        assert "Link" in response.headers
        links = response.headers.getall("Link")
        assert inList("canonical", links)
        assert not inList("webmention", links)
        assert "X-Pingback" not in response.headers

        blog.enable_linkbacks = True
        response = self.app.get('/post/' + post.slug)
        assert "Link" in response.headers
        links = response.headers.getall("Link")
        assert inList("canonical", links)
        assert inList("webmention", links)
        assert "X-Pingback" in response.headers

    def test_post(self):
        # no blog
        assert self.app.get('/post/nothing', status=404)

        self.createBlog()

        # no post
        assert self.app.get('/post/nothing', status=404)

        post = self.createPost()
        post.published = False
        assert self.app.get('/post/' + post.slug, status=404)

        post.published = True
        response = self.app.get('/post/' + post.slug)
        assert post.body in response


    def test_comment(self):
        # no blog
        assert self.app.post('/post/nothing', status=404)

        blog = self.createBlog()
        blog.moderation_alert = True
        blog.admin_email = "test.admin" + UCHAR + "@example.com"

        # comments still aren't enabled
        assert self.app.post('/post/nothing', status=404)

        blog.enable_comments = True

        # ip address in block list
        address = '127.0.0.1'
        self.testbed.setup_env(REMOTE_ADDR=address)
        blog.blocklist = [address]

        assert self.app.post('/post/nothing', status=404)

        blog.blocklist = []

        # still no post
        assert self.app.post('/post/nothing', status=404)

        post = self.createPost()
        post.published = False
        path = '/post/' + post.slug
        assert self.app.post(path, status=404)

        post.published = True
        data = {}
        data["body"] = "Test Comment Body" + UCHAR
        data["email"] = "test.comment" + UCHAR + "@example.com"
        data["name"] = ("Test Comment Name" + UCHAR).encode("utf-8")
        data["url"] = "http://www.example.com"
        data["token"] = token = self.getVerifyToken(path)

        # unapproved, so comment should not be there
        response = self.app.post(path, data)
        response = response.follow()
        assert data["body"] not in response

        # and a moderation email should've been sent
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert self.author.email in messages[0].to
        assert "Comment Awaiting Moderation" in messages[0].subject

        comment = self.createComment(post=post)
        comment.approved = True
        comment.put()

        # email now matches an approved comment, so it should work
        data["email"] = comment.email.encode("utf-8")
        response = self.app.post(path, data)
        response = response.follow()
        assert data["body"] in response
        assert data["name"] in response
        assert data["url"] in response
        assert data["email"] not in response

        # check that a new email wasn't sent
        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1

        # test using an author
        self.login(is_admin=True)
        data = {}
        data["body"] = ("Test Author Comment Body" + UCHAR).encode("utf-8")
        data["author_choice"] = "author"
        data["author"] = self.author.slug
        data["token"] = token

        response = self.app.post(path, data)
        response = response.follow()
        assert "(post author)" in response
        assert data["body"] in response


class TestTrackback(BaseTestController):

    def test_trackback(self):
        # no blog
        response = self.app.post('/trackback/nothing')
        assert '<error>1</error>' in response

        blog = self.createBlog()
        blog.moderation_alert = True
        blog.admin_email = "test.admin" + UCHAR + "@example.com"

        # linkbacks still aren't enabled
        response = self.app.post('/trackback/nothing')
        assert '<error>1</error>' in response

        blog.enable_linkbacks = True

        # ip address in block list
        address = '127.0.0.1'
        self.testbed.setup_env(REMOTE_ADDR=address)
        blog.blocklist = [address]

        response = self.app.post('/trackback/nothing')
        assert '<error>1</error>' in response

        blog.blocklist = []

        # still no post
        response = self.app.post('/trackback/nothing')
        assert '<error>1</error>' in response

        post = self.createPost()
        post.published = False
        path = '/trackback/' + post.slug
        response = self.app.post(path)
        assert '<error>1</error>' in response

        post.published = True
        data = {}
        data["excerpt"] = "Test Trackback Excerpt" + UCHAR
        data["blog_name"] = ("Test Trackback Blog Name" + UCHAR).encode("utf-8")
        data["title"] = ("Test Trackback Post Title" + UCHAR).encode("utf-8")
        data["url"] = "http://www.example.com/trackback-test"

        # unapproved, so comment should not be there
        response = self.app.post(path, data)
        assert '<error>0</error>' in response

        # and a moderation email should've been sent
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert self.author.email in messages[0].to
        assert "Trackback Awaiting Moderation" in messages[0].subject

        comment = self.createComment(post=post)
        comment.approved = True
        comment.trackback = True
        comment.url = data["url"]
        comment.name = data["title"]
        comment.blog_name = data["blog_name"]
        comment.body = data["excerpt"]
        comment.put()

        # url now matches an existing comment, so it should be rejected as redundant
        response = self.app.post(path, data)
        assert '<error>1</error>' in response

        # check that a new email wasn't sent
        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1

        # check that the approved one appears on the page
        response = self.app.get('/post/' + post.slug)
        assert 'Trackback' in response
        assert comment.url in response
        assert comment.name in response
        assert comment.blog_name in response
        assert comment.body in response


class TestPingback(BaseTestController):

    def test_pingback(self):
        # no blog
        params = ("http://www.example.com/pingback-test-source",)
        body = xmlrpclib.dumps(params, "nothing")
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Blog Not Found' in response

        blog = self.createBlog()
        blog.moderation_alert = True
        blog.admin_email = "test.admin" + UCHAR + "@example.com"

        # linkbacks still aren't enabled
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Access Denied' in response

        blog.enable_linkbacks = True

        # bad requests
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Unsupported Method' in response

        body = xmlrpclib.dumps(params, "pingback.ping")
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Invalid Request' in response

        params = (params[0], "not a url")
        body = xmlrpclib.dumps(params, "pingback.ping")
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Invalid Request' in response

        params = (params[0], "http://localhost/blog/post/")
        body = xmlrpclib.dumps(params, "pingback.ping")
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Post ID Not Found' in response

        # still no post
        params = (params[0], "http://localhost/blog/post/post-title")
        body = xmlrpclib.dumps(params, "pingback.ping")
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Post Not Found' in response

        # not published
        post = self.createPost()
        post.published = False
        params = (params[0], "http://localhost/blog/post/" + post.slug)
        body = xmlrpclib.dumps(params, "pingback.ping")
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Post Not Found' in response

        post.published = True

        # unapproved, so comment should not be there
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' not in response
        assert 'Pingback Receieved Successfully' in response

        # and a moderation email should've been sent
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert self.author.email in messages[0].to
        assert "Pingback Awaiting Moderation" in messages[0].subject

        comment = self.createComment(post=post)
        comment.approved = True
        comment.pingback = True
        comment.url = params[1]
        comment.put()

        # url now matches an existing comment, so it should be rejected as redundant
        response = self.app.request('/pingback', method='POST', body=body)
        assert '<fault>' in response
        assert 'Pingback Already Registered' in response

        # check that a new email wasn't sent
        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1

        # check that the approved one appears on the page
        response = self.app.get('/post/' + post.slug)
        assert 'Pingback' in response
        assert comment.url in response


class TestWebmention(BaseTestController):

    def test_webmention(self):
        # no blog
        data = {"source": "http://www.example.com/webmention-test-source"}
        assert self.app.post('/webmention', data, status=404)

        blog = self.createBlog()
        blog.moderation_alert = True
        blog.admin_email = "test.admin" + UCHAR + "@example.com"

        # linkbacks still aren't enabled
        assert self.app.post('/webmention', data, status=403)

        blog.enable_linkbacks = True

        # bad requests
        assert self.app.post('/webmention', data, status=400)

        data["target"] = "not a URL"
        assert self.app.post('/webmention', data, status=400)

        data["target"] = "http://localhost/blog/post/"
        assert self.app.post('/webmention', data, status=404)

        # still no post
        data["target"] = "http://localhost/blog/post/post-title"
        assert self.app.post('/webmention', data, status=404)

        # not published
        post = self.createPost()
        post.published = False
        data["target"] = "http://localhost/blog/post/" + post.slug
        assert self.app.post('/webmention', data, status=404)

        post.published = True

        # unapproved, so comment should not be there
        response = self.app.post('/webmention', data)
        assert 'Awaiting Moderation' in response

        # and a moderation email should've been sent
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert self.author.email in messages[0].to
        assert "Webmention Awaiting Moderation" in messages[0].subject

        comment = self.createComment(post=post)
        comment.approved = True
        comment.webmention = True
        comment.url = data["source"]
        comment.put()

        # url now matches an existing comment, so it should be rejected as redundant
        assert self.app.post('/webmention', data, status=400)

        # check that a new email wasn't sent
        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1

        # check that the approved one appears on the page
        response = self.app.get('/post/' + post.slug)
        assert 'Webmention' in response
        assert comment.url in response


class TestVerify(BaseTestController):

    def test_verify(self):
        data = {"url": "http://localhost/blog" }

        # no referer
        assert self.app.get('/verify', data, status=400)

        headers = [("referer", "http://localhost")]
        response = self.app.get('/verify', data, headers=headers)

        assert '"token":' in response
        

class TestAdmin(BaseTestController):

    def test_validateDT(self):
        valid, output = controller_admin.validateDT('')
        assert valid
        assert output is None

        valid, output = controller_admin.validateDT('2000-01-01 13:59:59')
        assert valid
        assert output == datetime.datetime(2000, 1, 1, 13, 59, 59)

    def test_admin(self):

        assert self.app.get('/admin', status=403)

        self.login(is_admin=True)

        # should redirect to setup the blog when one doesn't exist yet
        response = self.app.get('/admin')
        response = response.follow()
        assert '<h3>Blog Setup</h3>' in response

        self.createBlog()
        response = self.app.get('/admin')
        assert 'Admin</a></h2>' in response

    def test_blog(self):
        self.login(is_admin=True)

        response = self.app.get('/admin/blog')
        assert 'Admin - Blog' in response

        blog = self.createBlog()
        response = self.app.get('/admin/blog')
        assert blog.title in response

    def test_editBlog(self):
        self.login(is_admin=True)

        data = {}
        data["title"] = ('Test Blog Title' + UCHAR).encode('utf-8')
        data["description"] = ('Test Blog Description' + UCHAR).encode('utf-8')
        data["url"] = 'blog'
        data["posts_per_page"] = '10'
        data["image_preview_size"] = '600'
        data["mail_queue"] = 'mail'
        data["blocklist"] = '192.168.1.255,192.168.1.254'
        data["enable_comments"] = '1'
        data["enable_linkbacks"] = '1'
        data["author_pages"] = '1'
        data["admin_email"] = ('test.admin' + UCHAR + '@example.com').encode('utf-8')
        data["moderation_alert"] = '1'
        data["contact"] = '1'

        response = self.app.post('/admin/blog', data)
        response = response.follow()
        assert '<h3>Author</h3>' in response

    def test_authors(self):
        self.createBlog()
        self.login(is_admin=True)

        response = self.app.get('/admin/authors')
        assert 'Admin - Authors' in response

        author = self.createAuthor()
        response = self.app.get('/admin/authors')
        assert author.name in response

    def test_author(self):
        self.createBlog()
        self.login(is_admin=True)

        response = self.app.get('/admin/author/')
        assert 'Admin - Author' in response

        assert self.app.get('/admin/author/nothing', status=404)

        author = self.createAuthor()

        response = self.app.get('/admin/author/' + author.slug)
        assert 'Admin - Author - ' + author.name in response

    def test_editAuthor(self):
        self.createBlog()
        self.login(is_admin=True)

        data = {}
        data["name"] = ('Test Author Name' + UCHAR).encode('utf-8')
        data["url"] = 'http://www.example.com/test-author'
        data["email"] = ('test.author' + UCHAR + '@example.com').encode('utf-8')

        response = self.app.post('/admin/author/', data)
        response = response.follow()
        assert '<h3>Actions</h3>' in response

    def test_posts(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        response = self.app.get('/admin/posts')
        assert '<h3>Posts</h3>' in response
        assert 'No posts yet.' in response

        post = self.createPost(blog=blog)
        response = self.app.get('/admin/posts')
        assert post.title in response

    def test_deletePost(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        assert self.app.post('/admin/posts', {'post': 'nothing'}, status=404)

        post = self.createPost(blog=blog)

        response = self.app.post('/admin/posts', {'post': post.slug})
        response = response.follow()
        assert post.title not in response

    def test_post(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        response = self.app.get('/admin/post/')
        assert 'Save and Preview' in response
        assert 'Delete This Post' not in response

        assert self.app.get('/admin/post/nothing', status=404)

        post = self.createPost(blog=blog)
        response = self.app.get('/admin/post/' + post.slug)
        assert post.title in response
        assert 'Preview Mode' not in response

    def test_editPost(self):
        blog = self.createBlog()
        author = self.createAuthor(blog=blog)
        self.login(is_admin=True)

        data = {}
        data["title"] = ('Test Post Title' + UCHAR).encode('utf-8')
        data["slug_choice"] = 'auto'
        data["slug"] = ''
        data["author"] = author.slug
        data["body"] = ('Test Post Body' + UCHAR).encode('utf-8')
        data["tags"] = ('tag1, tag two ' + UCHAR).encode('utf-8')
        data["timestamp_choice"] = 'now'
        data["timestamp"] = ''
        data["preview"] = '1'

        response = self.app.post('/admin/post/', data)
        response = response.follow()
        assert data["title"] in response
        assert 'Preview Mode' in response
        assert 'tag1' in response

        data["slug_choice"] = 'custom'
        data["slug"] = 'test-slug'
        data["timestamp_choice"] = 'custom'
        data["timestamp"] = '2000-01-01 13:59:59'
        data["published"] = '1'

        response = self.app.post('/admin/post/test-post-title', data)
        response = response.follow()
        assert data["title"] in response
        assert 'Preview Mode' not in response

    def test_preview(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        assert self.app.get('/admin/preview/nothing', status=404)

        post = self.createPost(blog=blog)
        post.published = False
        response = self.app.get('/admin/preview/' + post.slug)
        assert post.title in response
        assert 'Preview Mode' in response

    def test_comments(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        response = self.app.get('/admin/comments')
        assert '<h3>Comments</h3>' in response
        assert 'No comments to moderate.' in response

        comment = self.createComment()
        response = self.app.get('/admin/comments')
        assert comment.body in response

    def test_moderateComment(self):
        blog = self.createBlog()
        blog.enable_comments = True
        self.login(is_admin=True)

        data = {'comment': 'nothing'}

        assert self.app.post('/admin/comments', data, status=404)

        # a simple delete
        comment = self.createComment()

        data = {'comment': comment.key.urlsafe(), 'delete': '1'}

        response = self.app.post('/admin/comments', data)
        response = response.follow()
        assert 'No comments to moderate.' in response

        # blocking the ip address, and redirecting back to the post page
        comment = self.createComment()
        comment.ip_address = '192.168.1.255'

        data = {'comment': comment.key.urlsafe(), 'block': '1', 'post': self.post.slug}

        response = self.app.post('/admin/comments', data)
        response = response.follow()
        assert self.post.title in response
        assert comment.body not in response

        response = self.app.get('/admin/comments')
        assert 'No comments to moderate.' in response

        # approving
        comment = self.createComment()

        data = {'comment': comment.key.urlsafe()}

        response = self.app.post('/admin/comments', data)
        response = response.follow()
        assert 'No comments to moderate.' in response

        # check that it made it to the page and email isn't visible
        response = self.app.get('/post/' + self.post.slug)
        assert comment.body in response
        assert comment.email not in response

    def test_images(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        response = self.app.get('/admin/images')
        assert '<h3>Images</h3>' in response
        assert 'No images stored in the database yet.' in response

        image = self.createImage(blog=blog)
        response = self.app.get('/admin/images')
        assert image.url in response

    def test_deleteImage(self):
        blog = self.createBlog()
        self.login(is_admin=True)

        # temporarily disable exception logging for this test to avoid messy printouts
        logging.disable(logging.CRITICAL)
        assert self.app.post('/admin/images', {'image': '0'}, status=404)
        logging.disable(logging.NOTSET)

        image = self.createImage(blog=blog)

        response = self.app.post('/admin/images', {'image': image.key.id()})
        response = response.follow()
        assert image.url not in response

    def test_image(self):
        self.createBlog()
        self.login(is_admin=True)

        # NOTE: this will fail in testing because webtest doesn't call dispatch on blob handlers for some reason
        #       so the session will never get properly created, but it works fine outside of testing
        #response = self.app.get('/admin/image')
        #assert "Admin - Upload an Image" in response

        response = self.app.get('/admin/image', {'json': '1'})
        assert '"url":' in response

    def test_migrate(self):
        self.createBlog()
        self.login(is_admin=True)

        assert self.app.get('/admin/migrate', status=405)

        assert self.app.post('/admin/migrate', status=302)

    def test_getCacheKeys(self):
        post = self.createPost()
        post.published = True

        keys = controller_admin.getCacheKeys(self.blog)
        assert keys == ['/blog', '/blog/contact', '/blog/feed', '/blog/post/test-post', '/blog/author/test-author']

    def test_getDatastoreKeys(self):
        post = self.createPost()
        post.published = True

        keys = controller_admin.getDatastoreKeys(self.blog)
        assert keys == [model.ndb.Key('HTMLCache', '/blog/feed')]

    def test_clearCache(self):
        post = self.createPost()
        post.published = True

        controller_admin.clearCache(self.blog)

        keys = controller_admin.getCacheKeys(self.blog)
        assert not memcache.get_multi(keys)


def inList(string, list):
    for item in list:
        if string in item:
            return True
    return False
