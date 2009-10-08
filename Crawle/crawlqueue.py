import sys, threading, Queue
import core

class CrawlQueue(object):
    """CrawlQueue is an abstract class in the sense that it needs to be
    subclassed with its get and put methods defined."""

    def get(self):
        """The get function must return a RequestResponse object."""
        raise "CrawlQueue.get() needs to be implemented"
    
    def put(self, queueItem):
        raise "CrawlQueue.put(queue_item) needs to be implemented"

class URLQueue(CrawlQueue):
    """URLQueue is the most basic queue type and is all that is needed for
    most situations. Simply, it queues full urls."""
	
    def __init__(self, seedfile=None):
        """Sets up the URLQueue by creating a queue.
        
        Keyword arguments:
        seedfile -- file containing urls to seed the queue (default None)
        """
        self.queue = Queue.Queue(0)

        # Add seeded items to the queue
        if seedfile:
            try:
                file = open(seedfile)
            except:
                raise "Could not open seed file"
            count = 0
            for line in file:
                self.queue.put(line.strip())
                count += 1
            file.close()
            print "Queued:", count
        else:
            print "Starting with empty queue"

    def save(self, file):
        """Outputs queue to file specified. On error prints queue to screen."""
        try:
            file = open(file, 'w')
        except:
            sys.stderr.write(' '.join(('Could not open file for saving.',
                                       'Printing to screen.\n')))
            sys.stderr.flush()
            file = sys.stdout

        items = 0
        while not self.queue.empty():
            try:
                item = self.queue.get(block=False)
                file.write("%s\n" % item)
                items += 1
            except Queue.Empty:
                print "Saving the queue is not atomic, FIXY TIME"

        if file != sys.stdout:
            file.close()

        print "Saved %d items." % items

    def get(self):
        """Return url at the head of the queue or None if empty"""
        size = self.queue.qsize()
        if size == 0: print "Queue empty"
        elif size % 1000 == 0: print "Queue Size: %d" % size

        try:
            url = self.queue.get(block=False)
            return core.RequestResponse(url)
        except Queue.Empty:
            return None

    def put(self, url):
        self.queue.put(url)
