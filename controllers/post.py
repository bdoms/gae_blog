from google.appengine.api import memcache

from base import FormController, cacheAndRender

from gae_blog.lib.gae_validators import validateBool, validateString, validateText, validateEmail, validateUrl
from gae_blog import model


class PostController(FormController):
    """ shows an individual post and saves comments to it """

    FIELDS = {"author_choice": validateString, "author": validateString, "email": validateEmail,
              "name": validateString, "url": validateUrl, "body": validateText,
              "trackback": validateBool, "blog_name": validateString, "pingback": validateBool,
              "webmention": validateBool}

    def headers(self):

        if self.blog and self.request.method != "POST":
            self.response.headers.add("Link", '<' + self.request.path_url + '>; rel="canonical"')

            root_url = self.request.host_url + self.blog_url

            if self.blog.enable_linkbacks:
                self.response.headers.add("X-Pingback", root_url + "/pingback")
                self.response.headers.add("Link", '<' + root_url + '/webmention>; rel="webmention"')

    @cacheAndRender(include_comments=True, skip_check=lambda controller: 'errors' in controller.session)
    def get(self, post_slug):

        if post_slug and self.blog:
            post = model.BlogPost.get_by_id(post_slug, parent=self.blog.key)
            if post and post.published:
                # only display a post if it's actually published
                form_data, errors = self.errorsFromSession()

                # the root URL and `include_comments` allow the trackback RDF to render correctly
                root_url = self.request.host_url + self.blog_url

                return self.renderTemplate('post.html', post=post, root_url=root_url,
                    form_data=form_data, errors=errors)

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

                    bot = self.botProtection('/post/' + post_slug)
                    if bot: return

                    form_data, errors, valid_data = self.validate()

                    valid_linkback = valid_data["trackback"] or valid_data["pingback"] or valid_data["webmention"]

                    if "body" not in errors:
                        # strip out all HTML to be on the safe side
                        body = model.stripHTML(valid_data["body"])

                        if body:
                            # turn URL's into links
                            body = model.linkURLs(body)
                            # finally, replace linebreaks with HTML linebreaks
                            body = body.replace("\r\n", "<br/>")
                        elif not valid_linkback:
                            errors["body"] = True

                    if valid_data["author_choice"] == "author":
                        # validate that if they want to comment as an author that it's valid and they're approved
                        if not self.user_is_admin:
                            return self.renderError(403)

                        author = model.BlogAuthor.get_by_id(valid_data["author"], parent=blog.key)
                        if not author:
                            errors["author"] = True

                        if not errors:
                            comment = model.BlogComment(body=body, approved=True, author=author.key, parent=post.key)
                            memcache.delete(self.request.path)
                    else:
                        # trackbacks require URLs, normal comments require emails if not from an author
                        if valid_linkback:
                            # must be admin to set linkbacks here and not through the normal paths
                            if not self.user_is_admin:
                                return self.renderError(403)

                            if not valid_data["url"]:
                                errors["url"] = True
                        elif not valid_data["email"]:
                            errors["email"] = True

                    if errors:
                        return self.redisplay(form_data, errors, self.blog_url + '/post/' + post_slug + '#comment-link')
                    elif valid_data["author_choice"] != "author":
                        # look for a previously approved comment from this email address on this blog
                        email = valid_data["email"]
                        approved = blog.comments.filter(model.BlogComment.email == email).filter(model.BlogComment.approved == True)

                        comment = model.BlogComment(email=email, body=body, ip_address=ip_address, parent=post.key)

                        if valid_data["name"]:
                            comment.name = valid_data["name"]
                        if valid_data["url"]:
                            comment.url = valid_data["url"]
                        if valid_data["trackback"]:
                            comment.trackback = True
                        if valid_data["blog_name"]:
                            comment.blog_name = valid_data["blog_name"]
                        if valid_data["pingback"]:
                            comment.pingback = True
                        if valid_data["webmention"]:
                            comment.webmention = True

                        if approved.count():
                            comment.approved = True
                            memcache.delete(self.request.path)
                        else:
                            self.linkbackEmail(post, comment)

                    comment.put()

                    return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')

        return self.renderError(404)
