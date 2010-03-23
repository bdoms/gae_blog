from base import BaseController

from gaeblog import model

class PostController(BaseController):
    """ shows an individual post and saves comments to it """
    def get(self, post_slug):

        if post_slug:
            blog = self.getBlog()
            post = model.BlogPost.all().filter("blog =", blog).filter("slug =", post_slug).get()
            if post and post.published:
                # only display a post if it's actually published
                return self.renderTemplate('post.html', post=post)

        return self.renderError(404)

    def post(self, post_slug):

        blog = self.getBlog()
        if blog and blog.comments:
            # only allow comment posting if comments are enabled
            if post_slug:
                post = model.BlogPost.all().filter("blog =", blog).filter("slug =", post_slug).get()
                if post and post.published:
                    # only allow commenting to a post if it's actually published
                    name = self.request.get("name")
                    url = self.request.get("url")
                    email = self.request.get("email")
                    body = self.request.get("body")

                    # TODO: validate that the email address and url are valid here

                    # TODO: validate that the body does not contain any unwanted HTML here

                    # TODO: turn any URL's in the body into anchor tags

                    # TODO: turn any linebreaks in the body into br tags

                    # TODO: make a way for the post author to bypass this check

                    # look for a previously approved comment from this email address on this blog
                    approved = []
                    for post in self.getBlog().posts:
                        approved.extend(list(post.comments.filter("email =", email).filter("approved =", True)))

                    comment = model.BlogComment(name=name, url=url, email=email, body=body, post=post)
                    if approved:
                        comment.approved = True
                    comment.put()

                    return self.redirect(self.blog_url + '/post/' + post_slug)

        return self.renderError(404)

