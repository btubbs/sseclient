import itertools
import io
try:
    from unittest import mock
except ImportError:
    import mock

import pytest
import requests
import six
from requests.cookies import RequestsCookieJar

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


def test_eols():
    for eol in ('\r\n', '\r', '\n'):
        m = E.parse('event: hello%sdata: eol%s' % (eol, eol))
        assert m.event == 'hello'
        assert m.data == 'eol'


class FakeResponse(object):
    def __init__(self, status_code, content, headers=None):
        self.status_code = status_code
        self.encoding = "utf-8"
        if not isinstance(content, six.text_type):
            content = content.decode("utf-8")
        self.stream = content
        self.headers = headers or None
        self.raw = io.BytesIO(content.encode())
    def raise_for_status(self):
        pass
    def iter_content(self, chunk_size=1024):
        return self.raw

def join_events(*events):
    """
    Given a bunch of Event objects, dump them all to strings and join them
    together.
    """
    return u''.join(e.dump() for e in events)


# Tests of parsing a multi event stream
def test_last_id_remembered(monkeypatch):
    content = u"data: message 1\nid: abcdef\n\ndata: message 2\n\n"
    fake_get = mock.Mock(return_value=FakeResponse(200, content))
    monkeypatch.setattr(requests, 'get', fake_get)

    c = sseclient.SSEClient('http://blah.com')
    m1 = next(c)
    m2 = next(c)

    assert m1.id == u'abcdef'
    assert m2.id is None
    assert c.last_id == u'abcdef'


def test_retry_remembered(monkeypatch):
    content = u"data: message 1\nretry: 5000\n\ndata: message 2\n\n"
    fake_get = mock.Mock(return_value=FakeResponse(200, content))
    monkeypatch.setattr(requests, 'get', fake_get)

    c = sseclient.SSEClient('http://blah.com')
    m1 = next(c)
    m2 = next(c)
    assert m1.retry == 5000
    assert m2.retry is None
    assert c.retry == 5000


def test_extra_newlines_after_event(monkeypatch):
    """
    This makes sure that extra newlines after an event don't
    cause the event parser to break as it did in
    https://github.com/btubbs/sseclient/issues/5.
    """
    content = u"""event: hello
data: hello1


event: hello
data: hello2

event: hello
data: hello3

"""
    fake_get = mock.Mock(return_value=FakeResponse(200, content))
    monkeypatch.setattr(requests, 'get', fake_get)

    c = sseclient.SSEClient('http://blah.com')
    m1 = next(c)
    m2 = next(c)
    m3 = next(c)

    assert m1.event == u'hello'
    assert m1.data == u'hello1'
    assert m2.data == u'hello2'
    assert m2.event == u'hello'
    assert m3.data == u'hello3'
    assert m3.event == u'hello'


@pytest.fixture
def multiple_responses(monkeypatch):
    content = join_events(
        E(data=u'message 1', id=u'first', retry=u'2000', event=u'blah'),
        E(data=u'message 2', id=u'second', retry=u'4000', event=u'blerg'),
        E(data=u'message 3\nhas two lines', id=u'third'),
    )
    fake_get = mock.Mock(return_value=FakeResponse(200, content))
    monkeypatch.setattr(requests, 'get', fake_get)

    yield

    fake_get.assert_called_once_with(
        'http://blah.com',
        headers={'Accept': 'text/event-stream', 'Cache-Control': 'no-cache'},
        stream=True)


def assert_multiple_messages(m1, m2, m3):
    assert m1.data == u'message 1'
    assert m1.id == u'first'
    assert m1.retry == 2000
    assert m1.event == u'blah'

    assert m2.data == u'message 2'
    assert m2.id == u'second'
    assert m2.retry == 4000
    assert m2.event == u'blerg'

    assert m3.data == u'message 3\nhas two lines'


@pytest.mark.usefixtures("multiple_responses")
def test_multiple_messages():
    c = sseclient.SSEClient('http://blah.com')
    m1 = next(c)
    m2 = next(c)
    m3 = next(c)

    assert_multiple_messages(m1, m2, m3)

    assert c.retry == m2.retry
    assert c.last_id == m3.id


@pytest.mark.usefixtures("multiple_responses")
def test_simple_iteration():
    c = sseclient.SSEClient('http://blah.com')
    m1, m2, m3 = itertools.islice(c, 3)

    assert_multiple_messages(m1, m2, m3)


def test_client_sends_cookies():
    s = requests.Session()
    s.cookies = RequestsCookieJar()
    s.cookies['foo'] = 'bar'
    with mock.patch('sseclient.requests.Session.send') as m:
        sseclient.SSEClient('http://blah.com', session=s)
        prepared_request = m.call_args[0][0]
        assert prepared_request.headers['Cookie'] == 'foo=bar'
