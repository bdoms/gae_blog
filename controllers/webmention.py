from base import BaseController

from gae_blog.lib.gae_validators import validateRequiredUrl
from gae_blog import model


class WebmentionController(BaseController):

    def get(self):

        return self.renderError(405)

    def post(self):

        # best technical resource on webmentions: https://github.com/converspace/webmention

        ip_address = self.request.remote_addr
        blog = self.blog

        if not blog:
            self.renderError(404)
        elif not blog.enable_linkbacks or ip_address in blog.blocklist:
            self.renderError(403)
        else:
            source = self.request.get("source")
            target = self.request.get("target")

            valid_source, source = validateRequiredUrl(source)
            valid_target, target = validateRequiredUrl(target)

            if not valid_source or not valid_target:
                self.renderError(400)
            else:
                root_url = self.request.host_url + self.blog_url + '/post/'
                post_slug = target.replace(root_url, '')
                if not post_slug:
                    self.renderError(404)
                else:
                    post = model.BlogPost.get_by_id(post_slug, parent=blog.key)

                    # only allow webmentions to a post if it's actually published
                    if not post or not post.published:
                        self.renderError(404)
                    else:
                        # look for a comment from this URL address on this blog already (redundancy check)
                        exists = post.comments.filter(model.BlogComment.url == source).filter(model.BlogComment.webmention == True)
                        if exists.count():
                            self.renderError(400)
                        else:
                            comment = model.BlogComment(url=source, webmention=True, ip_address=ip_address, parent=post.key)
                            comment.put()

                            self.linkbackEmail(post, comment)

                            self.response.set_status(202) # Accepted
                            self.response.out.write("Awaiting Moderation")
