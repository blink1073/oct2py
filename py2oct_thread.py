
import threading
import datetime
from py2oct import Octave


class ThreadClass(threading.Thread):
    def run(self):
        """ Create a unique instance of Octave and verify namespace uniqueness
        """
        oc = Octave()
        # write the same variable name in each thread and read it back
        oc.put('name', self.getName())
        name = oc.get('name')
        now = datetime.datetime.now()
        print "%s got '%s' at %s" % (self.getName(), name, now)
        assert self.getName() == name

if __name__ == '__main__':
    print "Starting 10 threads at %s" % datetime.datetime.now()
    for i in range(10):
        t = ThreadClass()
        t.start()
    print 'All threads started at %s' % datetime.datetime.now()