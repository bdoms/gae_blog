from google.appengine.api import memcache

from base import FormController, renderIfCachedNoErrors

from gae_blog.lib.gae_validators import validateString, validateRequiredText, validateEmail, validateUrl
from gae_blog import model


class PostController(FormController):
    """ shows an individual post and saves comments to it """

    FIELDS = {"author_choice": validateString, "author": validateString, "email": validateEmail,
              "name": validateString, "url": validateUrl, "body": validateRequiredText}

    @renderIfCachedNoErrors
    def get(self, post_slug):

        if post_slug and self.blog:
            post = model.BlogPost.get_by_id(post_slug, parent=self.blog.key)
            if post and post.published:
                # only display a post if it's actually published
                form_data, errors = self.errorsFromSession()
                return self.cacheAndRenderTemplate('post.html', post=post, form_data=form_data, errors=errors)

        return self.renderError(404)

    def post(self, post_slug):

        ip_address = self.request.remote_addr
        blog = self.blog
        if blog and blog.enable_comments and ip_address not in blog.blocklist:
            # only allow comment posting if comments are enabled
            if post_slug:
                post = model.BlogPost.get_by_id(post_slug, parent=blog.key)
                if post and post.published:
                    # only allow commenting to a post if it's actually published

                    bot = self.botProtection('/post/' + post_slug + '#comments')
                    if bot: return

                    form_data, errors, valid_data = self.validate()

                    if "body" not in errors:
                        # strip out all HTML to be on the safe side
                        body = model.stripHTML(valid_data["body"])

                        if body:
                            # turn URL's into links
                            body = model.linkURLs(body)
                            # finally, replace linebreaks with HTML linebreaks
                            body = body.replace("\r\n", "<br/>")
                        else:
                            errors["body"] = True

                    if valid_data["author_choice"] == "author":
                        # validate that if they want to comment as an author that it's valid and they're approved
                        if not self.user_is_admin:
                            return self.renderError(403)

                        author = model.BlogAuthor.get_by_id(valid_data["author"], parent=blog.key)
                        if not author:
                            errors["author"] = True

                        if errors:
                            self.errorsToSession(form_data, errors)
                            return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')

                        comment = model.BlogComment(body=body, approved=True, author=author.key, parent=post.key)
                        memcache.delete(self.request.path)
                    elif errors:
                        return self.redisplay(form_data, errors, self.blog_url + '/post/' + post_slug + '#comments')
                    else:
                        # look for a previously approved comment from this email address on this blog
                        email = valid_data["email"]
                        approved = blog.comments.filter(model.BlogComment.email == email).filter(model.BlogComment.approved == True)

                        comment = model.BlogComment(email=email, body=body, ip_address=ip_address, parent=post.key)

                        if valid_data["name"]:
                            comment.name = valid_data["name"]
                        if valid_data["url"]:
                            comment.url = valid_data["url"]

                        if approved.count():
                            comment.approved = True
                            memcache.delete(self.request.path)
                        elif blog.moderation_alert and blog.admin_email:
                            # send out an email to the author of the post if they have an email address
                            # informing them of the comment needing moderation
                            author = post.author.get()
                            if author.email:
                                if blog.title:
                                    subject = blog.title + " - Comment Awaiting Moderation"
                                else:
                                    subject = "Blog - Comment Awaiting Moderation"
                                comments_url = self.request.host_url + self.blog_url + "/admin/comments"
                                body = "A comment on your post \"" + post.title + "\" is waiting to be approved or denied at " + comments_url
                                self.deferEmail(author.name + " <" + author.email + ">", subject, body)

                    comment.put()

                    return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')

        return self.renderError(404)
