import xmlrpclib

from base import BaseController

from gae_blog.lib.gae_validators import validateRequiredUrl
from gae_blog import model


class PingbackController(BaseController):

    def get(self):

        return self.renderError(405)

    def post(self):

        # see the pingback specification for more info: http://hixie.ch/specs/pingback/pingback

        ip_address = self.request.remote_addr
        blog = self.blog
        result = None

        if not blog:
            result = xmlrpclib.Fault(32, 'Blog Not Found')
        elif not blog.enable_linkbacks or ip_address in blog.blocklist:
            result = xmlrpclib.Fault(49, 'Access Denied')
        else:
            params, methodname = xmlrpclib.loads(self.request.body)
            
            if methodname != 'pingback.ping':
                result = xmlrpclib.Fault(0, 'Unsupported Method')
            elif len(params) != 2:
                result = xmlrpclib.Fault(0, 'Invalid Request')
            else:
                source, target = params

                valid_source, source = validateRequiredUrl(source)
                valid_target, target = validateRequiredUrl(target)

                if not valid_source or not valid_target:
                    result = xmlrpclib.Fault(0, 'Invalid Request')
                else:
                    root_url = self.request.host_url + self.blog_url + '/post/'
                    post_slug = target.replace(root_url, '')
                    if not post_slug:
                        result = xmlrpclib.Fault(32, 'Post ID Not Found')
                    else:
                        post = model.BlogPost.get_by_id(post_slug, parent=blog.key)

                        # only allow pingbacking to a post if it's actually published
                        if not post or not post.published:
                            result = xmlrpclib.Fault(33, 'Post Not Found')
                        else:
                            # look for a comment from this URL address on this blog already (redundancy check)
                            exists = post.comments.filter(model.BlogComment.url == source).filter(model.BlogComment.pingback == True)
                            if exists.count():
                                result = xmlrpclib.Fault(48, 'Pingback Already Registered')
                        
                if not result:
                    comment = model.BlogComment(url=source, pingback=True, ip_address=ip_address, parent=post.key)
                    comment.put()

                    result = ('Pingback Receieved Successfully',)

                    self.linkbackEmail(post, comment)

        xml = xmlrpclib.dumps(result, methodresponse=True)

        self.response.headers['Content-Type'] = "text/xml"
        self.response.out.write(xml)
