from mock import patch

import sseclient
from sseclient import Event as E


# Some tests of parsing a single event string
def test_round_trip_parse():
    m1 = E(
        data='hi there\nsexy developer',
        event='salutation',
        id='abcdefg',
        retry=10000
    )

    dumped = m1.dump()
    m2 = E.parse(dumped)
    assert m1.id == m2.id
    assert m1.data == m2.data
    assert m1.retry == m2.retry
    assert m1.event == m2.event


def test_no_colon():
    m = E.parse('data')
    assert m.data == ''


def test_no_space():
    m = E.parse('data:hi')
    assert m.data == 'hi'


def test_comment():
    raw = ":this is a comment\ndata: this is some data"
    m = E.parse(raw)
    assert m.data == 'this is some data'


def test_retry_is_integer():
    m = E.parse('data: hi\nretry: 4000')
    assert m.retry == 4000


def test_default_event():
    m = E.parse('data: blah')
    assert m.event == 'message'


# A couple mocks for Requests
class FakeRequests(object):
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content

    def get(self, url, *args, **kwargs):
        return FakeResponse(self.status_code, self.content)


class FakeResponse(object):
    def __init__(self, status_code, content):
        self.status_code = status_code
        if not isinstance(content, unicode):
            content = content.decode('utf8')
        self.stream = content

    def iter_content(self, chunk_size=1, *args, **kwargs):
        try:
            c = self.stream[0]
            self.stream = self.stream[1:]
            yield c
        except IndexError:
            raise StopIteration

    def raise_for_status(self):
        pass


def join_events(*events):
    """
    Given a bunch of Event objects, dump them all to strings and join them
    together.
    """
    return ''.join(e.dump() for e in events)


# Tests of parsing a multi event stream
def test_last_id_remembered():
    content = "data: message 1\nid: abcdef\n\ndata: message 2\n\n"
    with patch('sseclient.requests', FakeRequests(200, content)):
        c = sseclient.SSEClient('http://blah.com')
        m1 = next(c)
        m2 = next(c)

        assert m1.id == u'abcdef'
        assert m2.id is None
        assert c.last_id == u'abcdef'


def test_retry_remembered():
    content = "data: message 1\nretry: 5000\n\ndata: message 2\n\n"
    with patch('sseclient.requests', FakeRequests(200, content)):
        c = sseclient.SSEClient('http://blah.com')
        m1 = next(c)
        m2 = next(c)
        assert m1.retry == 5000
        assert m2.retry is None
        assert c.retry == 5000


def test_multiple_messages():

    content = join_events(
        E(data='message 1', id='first', retry='2000', event='blah'),
        E(data='message 2', id='second', retry='4000', event='blerg'),
        E(data='message 3\nhas two lines', id='third'),
    )

    with patch('sseclient.requests', FakeRequests(200, content)):
        c = sseclient.SSEClient('http://blah.com')
        m1 = next(c)
        m2 = next(c)
        m3 = next(c)

        assert m1.data == u'message 1'
        assert m1.id == u'first'
        assert m1.retry == 2000
        assert m1.event == u'blah'

        assert m2.data == u'message 2'
        assert m2.id == u'second'
        assert m2.retry == 4000
        assert m2.event == u'blerg'

        assert m3.data == u'message 3\nhas two lines'

        assert c.retry == m2.retry
        assert c.last_id == m3.id
