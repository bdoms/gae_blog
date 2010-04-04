from google.appengine.api import users

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
                return self.renderTemplate('post.html', post=post, authors=blog.authors)

        return self.renderError(404)

    def post(self, post_slug):

        blog = self.getBlog()
        if blog and blog.comments:
            # only allow comment posting if comments are enabled
            if post_slug:
                post = model.BlogPost.all().filter("blog =", blog).filter("slug =", post_slug).get()
                if post and post.published:
                    # only allow commenting to a post if it's actually published

                    author_choice = self.request.get("author-choice")
                    author_key = self.request.get("author")
                    name = self.request.get("name")
                    url = self.request.get("url")
                    email = self.request.get("email")
                    body = self.request.get("body", "")

                    # TODO: validate that the email address and url are valid here

                    # just stripping out all HTML for now to be on the safe side
                    # TODO: allow some limited things (inline styles and links) in the future
                    body = model.stripHTML(body)

                    if author_choice == "author":
                        # validate that if they want to comment as an author that it's valid and they're approved
                        if not users.is_current_user_admin():
                            return self.renderError(403)
                        author = model.BlogAuthor.get(author_key)
                        if not author:
                            return self.renderError(400)

                        comment = model.BlogComment(body=body, approved=True, post=post, author=author)
                    else:
                        # look for a previously approved comment from this email address on this blog
                        approved = []
                        for post in self.getBlog().posts:
                            approved.extend(list(post.comments.filter("email =", email).filter("approved =", True)))

                        comment = model.BlogComment(name=name, url=url, email=email, body=body, post=post)
                        if approved:
                            comment.approved = True

                    comment.put()

                    return self.redirect(self.blog_url + '/post/' + post_slug + '#comments')

        return self.renderError(404)

