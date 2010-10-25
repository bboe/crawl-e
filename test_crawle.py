#!/usr/bin/env python
import crawle, socket, unittest

ADDRESS_0 = ('127.0.0.1', 80), False
ADDRESS_1 = ('127.0.0.1', 443), True
ADDRESS_2 = ('127.0.0.1', 8080), False

class TestCQueueLRU(unittest.TestCase):
    def setUp(self):
        self.lru = crawle.CQueueLRU(10, 10)

    def assert_newest(self, key):
        self.assertEqual(self.lru.table[key], self.lru.newest)
        self.assertEqual(None, self.lru.newest.prev)

    def assert_oldest(self, key):
        self.assertEqual(self.lru.table[key], self.lru.oldest)
        self.assertEqual(None, self.lru.oldest.next)

    def testGetSingleItem(self):
        item = self.lru[ADDRESS_0]
        self.assertEqual(None, self.lru.newest)
        self.assertEqual(None, self.lru.oldest)

    def testPutSingleItem(self):
        item = self.lru[ADDRESS_0]
        self.lru[ADDRESS_0] = item
        self.assertEqual(1, len(self.lru.table))
        self.assert_newest(ADDRESS_0)
        self.assert_oldest(ADDRESS_0)

    def testReAddSingleItem(self):
        item = self.lru[ADDRESS_0]
        self.lru[ADDRESS_0] = item
        again = self.lru[ADDRESS_0]
        self.assertEqual(again, item)
        self.lru[ADDRESS_0] = again
        self.assertEqual(1, len(self.lru.table))
        self.assert_newest(ADDRESS_0)
        self.assert_oldest(ADDRESS_0)

    def testPutDoubleItemLimit1(self):
        self.lru.max_queues = 1
        item0 = self.lru[ADDRESS_0]
        item1 = self.lru[ADDRESS_1]
        self.lru[ADDRESS_0] = item0
        self.lru[ADDRESS_1] = item1
        self.assertEqual(1, len(self.lru.table))
        self.assert_newest(ADDRESS_1)
        self.assert_oldest(ADDRESS_1)

    def testPutDoubleItemLimitN(self):
        item0 = self.lru[ADDRESS_0]
        item1 = self.lru[ADDRESS_1]
        self.lru[ADDRESS_0] = item0
        self.lru[ADDRESS_1] = item1
        self.assertEqual(2, len(self.lru.table))
        self.assert_newest(ADDRESS_1)
        self.assert_oldest(ADDRESS_0)

    def testReAddFirstOfDoubleItemLimitN(self):
        item0 = self.lru[ADDRESS_0]
        item1 = self.lru[ADDRESS_1]
        self.lru[ADDRESS_0] = item0
        self.lru[ADDRESS_1] = item1
        self.lru[ADDRESS_0] = item0
        self.assertEqual(2, len(self.lru.table))
        self.assert_newest(ADDRESS_0)
        self.assert_oldest(ADDRESS_1)

    def testReAddSecondOfDoubleItemLimitN(self):
        item0 = self.lru[ADDRESS_0]
        item1 = self.lru[ADDRESS_1]
        self.lru[ADDRESS_0] = item0
        self.lru[ADDRESS_1] = item1
        self.lru[ADDRESS_1] = item0
        self.assertEqual(2, len(self.lru.table))
        self.assert_newest(ADDRESS_1)
        self.assert_oldest(ADDRESS_0)

    def testPutTripleItemLimitN(self):
        item0 = self.lru[ADDRESS_0]
        item1 = self.lru[ADDRESS_1]
        item2 = self.lru[ADDRESS_2]
        self.lru[ADDRESS_0] = item0
        self.lru[ADDRESS_1] = item1
        self.lru[ADDRESS_2] = item2
        self.assertEqual(3, len(self.lru.table))
        self.assert_newest(ADDRESS_2)
        self.assert_oldest(ADDRESS_0)

    def testRAddMiddleOfTripleItemLimitN(self):
        item0 = self.lru[ADDRESS_0]
        item1 = self.lru[ADDRESS_1]
        item2 = self.lru[ADDRESS_2]
        self.lru[ADDRESS_0] = item0
        self.lru[ADDRESS_1] = item1
        self.lru[ADDRESS_2] = item2
        self.lru[ADDRESS_1] = item1
        self.assertEqual(3, len(self.lru.table))
        self.assert_newest(ADDRESS_1)
        self.assert_oldest(ADDRESS_0)
        self.assertEqual(self.lru.newest, self.lru.oldest.prev.prev)
        self.assertEqual(self.lru.oldest, self.lru.newest.next.next)


class TestHTTPConnectionQueue(unittest.TestCase):
    def setUp(self):
        self.cq = crawle.HTTPConnectionQueue(ADDRESS_0)

    def testQueueLength(self):
        temp = self.cq.get()
        for i in range(5):
            self.assertEqual(self.cq.queue.qsize(), i)
            self.cq.put(temp)

    def testResetConnection(self):
        prev = crawle.HTTPConnectionQueue.REQUEST_LIMIT
        try:
            crawle.HTTPConnectionQueue.REQUEST_LIMIT = 2
            a = self.cq.get()
            self.cq.put(a)
            self.assertEqual(self.cq.get(), a)
            self.cq.put(a)
            self.assertNotEqual(self.cq.get(), a)
        finally:
            crawle.HTTPConnectionQueue.REQUEST_LIMIT = prev

    def testGetConnectionCount(self):
        for i in range(5):
            conn = self.cq.get()
            self.assertEqual(conn.request_count, 0)

    def testGetConnectionCountReplace(self):
        for i in range(5):
            conn = self.cq.get()
            self.assertEqual(conn.request_count, i)
            self.cq.put(conn)

    def testLimitConnections(self):
        self.cq.max_conn = 1
        item0 = self.cq.connection_object(*ADDRESS_0)
        item1 = self.cq.connection_object(*ADDRESS_0)
        self.cq.put(item0)
        self.cq.put(item1)
        self.assertEqual(1, self.cq.queue.qsize())
        self.assertEqual(item0, self.cq.get())
        self.assertEqual(0, self.cq.queue.qsize())


class TestHTTPConnectionControl(unittest.TestCase):
    def setUp(self):
        self.cc = crawle.HTTPConnectionControl(crawle.Handler())

    def testRequestSTOP_CRAWLE(self):
        crawle.STOP_CRAWLE = True
        rr = crawle.RequestResponse('')
        try:
            self.cc.request(rr)
            self.fail('Did not raise CRAWL-E Stopped exception.')
        except Exception, e:
            self.assertEqual('CRAWL-E Stopped', e.args[0])
        finally:
            crawle.STOP_CRAWLE = False

    def testRequestPreProcess(self):
        rr = crawle.RequestResponse('http://google.com')
        self.cc.handler = PreProcessFailHandler()
        try:
            self.cc.request(rr)
            self.fail('Did not raise Aborted in pre_process exception.')
        except Exception, e:
            self.assertEqual('Aborted in pre_process', e.args[0])

    def testRequestInvalidMethod(self):
        rr = crawle.RequestResponse('http://www.google.com', method='INVALID')
        self.cc.request(rr)
        self.assertEqual(405, rr.response_status)

    def testRequestInvalidHostname(self):
        rr = crawle.RequestResponse('http://invalid')
        try:
            self.cc.request(rr)
            self.fail('Did not raise invalid hostname exception')
        except socket.gaierror, e:
            self.assertEqual(-5, e.errno)

    def testRequestInvalidURL(self):
        urls = ['invalid', 'http:///invalid', 'httpz://google.com']
        for url in urls:
            rr = crawle.RequestResponse(url)
            try:
                self.cc.request(rr)
                self.fail('Did not raise Invalid URL exception.')
            except Exception, e:
                self.assertEqual('Invalid URL scheme', e.args[0])

    def testRequest301(self):
        rr = crawle.RequestResponse('http://google.com', redirects=None)
        self.cc.request(rr)
        self.assertEqual(301, rr.response_status)
        self.assertEqual('http://www.google.com/',
                         rr.response_headers['location'])

    def testRequestRedirectExceeded(self):
        rr = crawle.RequestResponse('http://google.com', redirects=0)
        try:
            self.cc.request(rr)
            self.fail('Did not raise redirect count exceeeded exception.')
        except Exception, e:
            self.assertEqual('Redirect count exceeded', e.args[0])

    def testRequestSuccessfulRedirect(self):
        rr = crawle.RequestResponse('http://google.com', redirects=1)
        self.cc.request(rr)
        self.assertEqual(200, rr.response_status)
        self.assertEqual(0, rr.redirects)

    def testRequest200(self):
        rr = crawle.RequestResponse('http://www.google.com', redirects=1)
        self.cc.request(rr)
        self.assertEqual(200, rr.response_status)
        self.assertEqual(1, rr.redirects)
        self.assertTrue(rr.response_time > 0)

    def testHTTPSRequest200(self):
        # Page that can only be accessed via https, http causes redirect
        url = 'https://msp.f-secure.com/web-test/common/test.html'
        rr = crawle.RequestResponse(url, redirects=1)
        self.cc.request(rr)
        self.assertEqual(200, rr.response_status)
        self.assertEqual(1, rr.redirects)
        self.assertTrue(rr.response_time > 0)

    def testRequestGzip(self):
        rr = crawle.RequestResponse('http://www.pricetrackr.com/robots.txt',
                                    redirects=1)
        self.cc.request(rr)
        self.assertEqual(200, rr.response_status)
        self.assertEqual(1, rr.redirects)
        self.assertTrue(rr.response_time > 0)
        self.assertTrue('User-agent' in rr.response_body)

    def testRequestPost(self):
        rr = crawle.RequestResponse(
            'http://www.snee.com/xml/crud/posttest.cgi', method='POST',
            params={'fname':'CRAWL-E', 'lname':'POST_TEST'})
        self.cc.request(rr)
        self.assertEqual(200, rr.response_status)
        self.assertTrue(rr.response_time > 0)
        self.assertTrue(''.join(['<p>First name: "CRAWL-E"</p>',
                                 '<p>Last name: "POST_TEST"</p>'])
                        in rr.response_body)


class TestController(unittest.TestCase):
    def testInit(self):
        c = crawle.Controller(None, None, 1)


###
# HELPER CLASSES
###
class PreProcessFailHandler(crawle.Handler):
    def pre_process(self, req_res): req_res.response_url = None

    
if __name__ == '__main__':
    unittest.main()
