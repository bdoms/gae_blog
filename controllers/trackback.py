from base import FormController

from gae_blog.lib.gae_validators import validateString, validateText, validateRequiredUrl
from gae_blog import model


class TrackbackController(FormController):

    FIELDS = {"title": validateString, "excerpt": validateText, "url": validateRequiredUrl, "blog_name": validateString}

    def get(self, post_slug):

        return self.renderError(405)

    def post(self, post_slug):

        # this is probably the best resource for more info about trackback: http://www.sixapart.com/labs/trackback/

        ip_address = self.request.remote_addr
        blog = self.blog
        error = ''

        if not blog:
            error = 'There is no blog at this URL.'
        elif not blog.enable_linkbacks or ip_address in blog.blocklist:
            error = 'This blog does not have trackbacks enabled.'
        elif not post_slug:
            error = 'Missing post ID.'
        else:
            post = model.BlogPost.get_by_id(post_slug, parent=blog.key)
            # only allow trackbacking to a post if it's actually published
            if not post or not post.published:
                error = 'There is no post with ID ' + post_slug
            else:
                form_data, errors, valid_data = self.validate()

                if errors:
                    error = 'Invalid request.'
                else:
                    excerpt = valid_data["excerpt"]
                    if excerpt:
                        # strip out all HTML to be on the safe side
                        excerpt = model.stripHTML(excerpt)

                        if excerpt:
                            # turn URL's into links
                            excerpt = model.linkURLs(excerpt)
                            # finally, replace linebreaks with HTML linebreaks
                            excerpt = excerpt.replace("\r\n", "<br/>")

                    url = valid_data["url"]
                    if url:
                        # look for a comment from this URL address on this blog already (redundancy check)
                        exists = post.comments.filter(model.BlogComment.url == url).filter(model.BlogComment.trackback == True)
                        if exists.count():
                            error = 'This trackback already exists.'

                if not error:
                    comment = model.BlogComment(url=url, trackback=True, ip_address=ip_address, parent=post.key)

                    if valid_data["title"]:
                        comment.name = valid_data["title"]
                    if excerpt:
                        comment.body = excerpt
                    if valid_data["blog_name"]:
                        comment.blog_name = valid_data["blog_name"]

                    comment.put()

                    self.linkbackEmail(post, comment)

        self.renderTemplate('trackback.xml', error=error)
