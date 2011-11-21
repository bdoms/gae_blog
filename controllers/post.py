from google.appengine.api import mail, memcache

from base import BaseController, renderIfCached

from gae_blog import model
from gae_blog.formencode.validators import UnicodeString, Email, URL

class PostController(BaseController):
    """ shows an individual post and saves comments to it """

    @renderIfCached
    def get(self, post_slug):

        if post_slug:
            blog = self.getBlog()
            post = model.BlogPost.get_by_key_name(post_slug, parent=blog)
            if post and post.published:
                # only display a post if it's actually published
                return self.cacheAndRenderTemplate('post.html', post=post)

        return self.renderError(404)

    def post(self, post_slug):

        ip_address = self.request.remote_addr
        blog = self.getBlog()
        if blog and blog.enable_comments and ip_address not in blog.blocklist:
            # only allow comment posting if comments are enabled
            if post_slug:
                post = model.BlogPost.get_by_key_name(post_slug, parent=blog)
                if post and post.published:
                    # only allow commenting to a post if it's actually published

                    author_choice = self.request.get("author-choice")
                    author_slug = self.request.get("author")
                    name = self.request.get("name")
                    url = self.request.get("url")
                    email = self.request.get("email")
                    body = self.request.get("body", "")

                    # body validation and handling
                    body = self.validate(UnicodeString(not_empty=True), body, "Comment")
                    if not body: return

                    # strip out all HTML to be on the safe side
                    body = model.stripHTML(body)

                    # turn URL's into links
                    body = model.linkURLs(body)

                    # finally, replace linebreaks with HTML linebreaks
                    body = body.replace("\r\n", "<br/>")

                    if author_choice == "author":
                        # validate that if they want to comment as an author that it's valid and they're approved
                        if not self.isUserAdmin():
                            return self.renderError(403)
                        author = model.BlogAuthor.get_by_key_name(author_slug, parent=blog)
                        if not author:
                            return self.renderError(400)

                        comment = model.BlogComment(body=body, approved=True, author=author, parent=post)
                        memcache.delete(self.request.path + self.request.query_string)
                    else:
                        # validate that the email address is valid
                        email = self.validate(Email(), email, "Email")
                        if not email: return

                        # validate that the name, if present, is valid
                        if name:
                            name = self.validate(UnicodeString(max=500), name, "Name")
                            if not name: return
                            name = model.stripHTML(name)

                        # validate that the url, if present, is valid
                        if url:
                            url = self.validate(URL(add_http=True), url, "URL")
                            if not url: return

                        # look for a previously approved comment from this email address on this blog
                        approved = blog.comments.filter("email =", email).filter("approved =", True)

                        comment = model.BlogComment(email=email, body=body, ip_address=ip_address, parent=post)
                        if name:
                            comment.name = name
                        if url:
                            comment.url = url

                        if approved.count():
                            comment.approved = True
                            memcache.delete(self.request.path + self.request.query_string)
                        elif blog.moderation_alert and blog.admin_email:
                            # send out an email to the author of the post if they have an email address
                            # informing them of the comment needing moderation
                            author = post.author
                            if author.email:
                                if blog.title:
                                    subject = blog.title + " - Comment Awaiting Moderation"
                                else:
                                    subject = "Blog - Comment Awaiting Moderation"
                                comments_url = "http://" + self.request.headers.get('host', '') + blog.url + "/admin/comments"
                                body = "A comment on your post \"" + post.title + "\" is waiting to be approved or denied at " + comments_url
                                mail.send_mail(sender=blog.admin_email, to=author.name + " <" + author.email + ">", subject=subject, body=body)

                    comment.put()

                    return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')

        return self.renderError(404)

