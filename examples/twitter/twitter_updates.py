#!/usr/bin/env python
import getpass, re, sys, threading
import crawle

class TwitterHandler(crawle.Handler):
    """This is an example of doing authentication with CRAWL-E.

    It must first be noted that twitter's robots.txt file disallows crawling
    thus proceed at your own risk.
    """

    TWITTER_SESS_RE = re.compile('(_twitter_sess=[^;]+;)')
    AUTH_TOKEN_RE = re.compile('<input id="authenticity_token" name="authenticity_token" type="hidden" value="([a-z0-9]+)"')
    LOGIN_PAGE_URL = 'http://twitter.com/login'
    LOGIN_POST_URL = 'https://twitter.com/sessions'

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = None
	self.lock = threading.Lock()
	self.exit = False

    def login(self, body):
        """ Using CRAWL-E's connection framework authenticate with Twitter
        and extract cookie data"""

        match = self.AUTH_TOKEN_RE.search(body)
        if not match or len(match.groups()) != 1:
            return False

        auth_token = match.group(1)
        params = {'authenticity_token':auth_token,
                  'session[username_or_email]':self.username,
                  'session[password]':self.password,
                  'commit':'Sign In'}

        cc = crawle.HTTPConnectionControl(crawle.Handler())
        rr = crawle.RequestResponse(self.LOGIN_POST_URL, method='POST',
                                    params=params, redirects=None)
        cc.request(rr)
        if rr.response_status != 302:
            return False
        match = self.TWITTER_SESS_RE.search(rr.response_headers['set-cookie'])
        if not match or len(match.groups()) != 1:
            return False
        self.session = match.group(1)
        return True

    def pre_process(self, req_res):
        self.lock.acquire()
        if self.session:
            req_res.request_headers = {'cookie':self.session}
        self.lock.release()

    def process(self, req_res, queue):
        if req_res.response_status != 200:
            print "%d - putting %s back on queue" % (req_res.response_status,
                                                     req_res.response_url)
            queue.put(req_res.response_url)
            return

        # Test if a login is required, if so login then readd the request URL
        if req_res.response_url == self.LOGIN_PAGE_URL:
            self.lock.acquire()
            login_status = self.login(req_res.response_body)
            self.lock.release()
            if login_status:
                queue.put(req_res.request_url)
            else:
                print 'Login failed'
            return

        print req_res.response_body
        return				

    def stop(self):
        self.exit = True
        self.output.close()

if __name__ == '__main__':
    print "This is broken for now"
    sys.exit(1)

    username = raw_input('Username: ')
    password = getpass.getpass()

    twitter_handler = TwitterHandler(username, password)
    queue = crawle.URLQueue()
    queue.queue.put('http://twitter.com/following')
    controller = crawle.Controller(handler=twitter_handler, queue=queue,
                                   num_threads=1)
    controller.start()
    try:
        controller.join()
    except KeyboardInterrupt:
        controller.stop()
    queue.save('uncrawled_urls')
