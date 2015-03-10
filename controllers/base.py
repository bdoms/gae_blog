# the base file and class for all controllers to inherit from

# standard library
import json
import logging
import os
from datetime import datetime, timedelta
from hashlib import sha512

# app engine api imports
from google.appengine.api import mail, memcache, users
from google.appengine.ext import deferred

# app engine included libraries imports
import jinja2
import webapp2
from webapp2_extras import sessions

# local
from gae_blog.config import TEMPLATES_PATH
from gae_blog import model

# see if caching is available
try:
    from gae_html import cacheAndRender
except ImportError:
    def cacheAndRender(**top_kwargs):
        def wrap_action(action):
            def decorate(*args,  **kwargs):
                return action(*args, **kwargs)
            return decorate
        return wrap_action

# see if asset management is available
try:
    from gae_deploy import static
except ImportError:
    def static(url):
        return url


class RelativeEnvironment(jinja2.Environment):
    """ enable relative template paths """

    def join_path(self, template, parent):
        return os.path.join(os.path.dirname(parent), template)


class RelativeLoader(jinja2.BaseLoader):
    """ enable relative template paths """

    def get_source(self, environment, template):
        path = os.path.realpath(os.path.join(TEMPLATES_PATH, template))
        if not os.path.exists(path):
            raise jinja2.TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with file(path) as f:
            source = f.read().decode('utf-8')
        return source, path, lambda: mtime == os.path.getmtime(path)


class BaseController(webapp2.RequestHandler):

    jinja_env = RelativeEnvironment(loader=RelativeLoader())

    def dispatch(self):
        # get a session store for this request
        self.session_store = sessions.get_store(request=self.request)

        if hasattr(self, "headers"):
            self.headers()

        webapp2.RequestHandler.dispatch(self)

        # save all sessions
        self.session_store.save_sessions(self.response)

    def getSession(self):
        return self.session_store.get_session()

    @webapp2.cached_property
    def session(self):
        # uses the default cookie key
        return self.getSession()

    def compileTemplate(self, filename, **kwargs):
        template = self.jinja_env.get_template(filename)
        # add some standard variables
        kwargs["blog_url"] = self.blog_url
        kwargs["blog"] = self.blog
        if self.blog and self.blog.template:
            kwargs["blog_base"] = '../../' + self.blog.template
        else:
            kwargs["blog_base"] = 'default_base.html'
        kwargs["user"] = self.user
        if self.user:
            kwargs["user_is_admin"] = self.user_is_admin
        kwargs["static"] = static
        return template.render(kwargs)

    def renderTemplate(self, filename, **kwargs):
        if self.request.method != 'HEAD':
            self.response.out.write(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int, stacktrace=None):
        self.response.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.response.headers['Content-Type'] = "application/json"
        if self.request.method != 'HEAD':
            self.response.out.write(json.dumps(data, ensure_ascii=False, encoding='utf-8'))

    def head(self, *args):
        # support HEAD requests in a generic way
        self.get(*args)
        # the output may be cached, but still don't send it to save bandwidth
        self.response.clear()

    # this overrides the base class for handling things like 500 errors
    def handle_exception(self, exception, debug):
        # log the error
        logging.exception(exception)

        # if this is development, then print out a stack trace
        stacktrace = None
        if os.environ.get('SERVER_SOFTWARE', '').startswith('Development') or self.user_is_admin:
            import traceback
            stacktrace = traceback.format_exc()

        # if the exception is a HTTPException, use its error code
        # otherwise use a generic 500 error code
        if isinstance(exception, webapp2.HTTPException):
            status_int = exception.code
        else:
            status_int = 500

        self.renderError(status_int, stacktrace=stacktrace)

    def getUser(self):
        return users.get_current_user()

    def isUserAdmin(self):
        return users.is_current_user_admin()

    @webapp2.cached_property
    def user(self):
        return self.getUser()

    @webapp2.cached_property
    def user_is_admin(self):
        return self.isUserAdmin()

    @webapp2.cached_property
    def blog(self):
        return model.Blog.get_by_id(self.blog_slug)

    @webapp2.cached_property
    def blog_slug(self):
        return self.request.path.split('/')[1] # we add the slash for easy URL making

    @webapp2.cached_property
    def blog_url(self):
        return '/' + self.blog_slug

    def errorsFromSession(self):
        form_data = self.session.pop("form_data", {})
        errors = self.session.pop("errors", {})
        return form_data, errors

    @classmethod
    def sendEmail(cls, sender, to, subject, body, reply_to=None):
        if reply_to:
            mail.send_mail(sender=sender, to=to, subject=subject, body=body, reply_to=reply_to)
        else:
            mail.send_mail(sender=sender, to=to, subject=subject, body=body)

    def deferEmail(self, to, subject, body, reply_to=None, **kwargs):
        deferred.defer(self.sendEmail, self.blog.admin_email, to, subject, body, reply_to=reply_to, _queue=self.blog.mail_queue)

    def linkbackEmail(self, post, comment):
        blog = self.blog
        if blog.moderation_alert and blog.admin_email:
            # send out an email to the author of the post if they have an email address
            # informing them of the comment needing moderation
            author = post.author.get()
            if author.email:
                if comment.trackback:
                    linkback = "Trackback"
                elif comment.pingback:
                    linkback = "Pingback"
                elif comment.webmention:
                    linkback = "Webmention"
                else:
                    linkback = "Comment"
                if blog.title:
                    subject = blog.title + " - " + linkback + " Awaiting Moderation"
                else:
                    subject = "Blog - " + linkback + " Awaiting Moderation"
                comments_url = self.request.host_url + self.blog_url + "/admin/comments"
                body = "A " + linkback + " on your post \"" + post.title + "\" is waiting to be approved or denied at " + comments_url
                self.deferEmail(author.name + " <" + author.email + ">", subject, body)


class FormController(BaseController):

    # a mapping of field names to their validator functions
    FIELDS = {}
    SALT_KEY = "GAE_BLOG_VERIFY_SALT"

    def validate(self):
        form_data = {} # all the original request data, for potentially re-displaying
        errors = {} # only fields with errors
        valid_data = {} # only valid fields

        for name, validator in self.FIELDS.items():
            try:
                form_data[name] = self.request.get(name)
            except UnicodeDecodeError:
                return self.renderError(400)
            
            valid, data = validator(form_data[name])
            if valid:
                valid_data[name] = data
            else:
                errors[name] = True

        return form_data, errors, valid_data

    def redisplay(self, form_data, errors, url):
        self.session["form_data"] = form_data
        self.session["errors"] = errors
        self.redirect(url)

    def botProtection(self, url):
        # returns if the request is suspected of being a bot or not
        try:
            honeypot = self.request.get("required")
            token = self.request.get("token")
        except UnicodeDecodeError:
            self.renderError(400)
            return True

        if honeypot:
            # act perfectly normal so the bot thinks the request worked
            self.redirect(self.blog_url + url)
            return True

        now = datetime.utcnow()
        challenge = self.generateToken(self.request.url, timestamp=now)
        if token != challenge:
            now -= timedelta(minutes=1)
            challenge = self.generateToken(self.request.url, timestamp=now)
            if token != challenge:
                # act perfectly normal so the bot thinks the request worked
                self.redirect(self.blog_url + url)
                return True

        return False

    def generateToken(self, url, timestamp=None):
        salt = memcache.get(self.SALT_KEY)
        if not salt:
            salt = os.urandom(64).encode('base64')
            memcache.set(self.SALT_KEY, salt)
        if not timestamp:
            timestamp = datetime.utcnow()
        return sha512(url + salt + timestamp.strftime("%Y%m%d%H%M")).hexdigest()
