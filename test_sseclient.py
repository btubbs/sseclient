#!/usr/bin/env python
"""Tests for sseclient package."""
#
# Distributed under the terms of the MIT license.
#
from __future__ import unicode_literals

import itertools
import io
import json
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
    def __init__(self, status_code, content, headers=None, encoding="utf-8"):
        self.status_code = status_code
        self.encoding = encoding
        self.apparent_encoding = "utf-8"
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
    return ''.join(e.dump() for e in events)


# Tests of parsing a multi event stream
@pytest.mark.parametrize("encoding", ["utf-8", None])
def test_last_id_remembered(monkeypatch, encoding):
    content = 'data: message 1\nid: abcdef\n\ndata: message 2\n\n'
    fake_get = mock.Mock(return_value=FakeResponse(200, content, encoding=encoding))
    monkeypatch.setattr(requests, 'get', fake_get)

    c = sseclient.SSEClient('http://blah.com')
    m1 = next(c)
    m2 = next(c)

    assert m1.id == 'abcdef'
    assert m2.id is None
    assert c.last_id == 'abcdef'


def test_retry_remembered(monkeypatch):
    content = 'data: message 1\nretry: 5000\n\ndata: message 2\n\n'
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
    content = """event: hello
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

    assert m1.event == 'hello'
    assert m1.data == 'hello1'
    assert m2.data == 'hello2'
    assert m2.event == 'hello'
    assert m3.data == 'hello3'
    assert m3.event == 'hello'


@pytest.fixture
def multiple_responses(monkeypatch):
    content = join_events(
        E(data='message 1', id='first', retry='2000', event='blah'),
        E(data='message 2', id='second', retry='4000', event='blerg'),
        E(data='message 3\nhas two lines', id='third'),
    )
    fake_get = mock.Mock(return_value=FakeResponse(200, content))
    monkeypatch.setattr(requests, 'get', fake_get)

    yield

    fake_get.assert_called_once_with(
        'http://blah.com',
        headers={'Accept': 'text/event-stream', 'Cache-Control': 'no-cache'},
        stream=True)


def assert_multiple_messages(m1, m2, m3):
    assert m1.data == 'message 1'
    assert m1.id == 'first'
    assert m1.retry == 2000
    assert m1.event == 'blah'

    assert m2.data == 'message 2'
    assert m2.id == 'second'
    assert m2.retry == 4000
    assert m2.event == 'blerg'

    assert m3.data == 'message 3\nhas two lines'


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
        m.return_value.encoding = "utf-8"
        sseclient.SSEClient('http://blah.com', session=s)
        prepared_request = m.call_args[0][0]
        assert prepared_request.headers['Cookie'] == 'foo=bar'

@pytest.fixture
def unicode_multibyte_responses(monkeypatch):
    content = join_events(
        E(data='ööööööööööööööööööööööööööööööööööööööööööööööööööööööööö', id='first', retry='2000', event='blah'),
        E(data='äääääääääääääääääääääääääääääääääääääääääääääääääääääääää', id='second', retry='4000', event='blerg'),
        E(data='üüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüü', id='third'),
    )
    fake_get = mock.Mock(return_value=FakeResponse(200, content))
    monkeypatch.setattr(requests, 'get', fake_get)

    yield

    fake_get.assert_called_once_with(
        'http://blah.com',
        headers={'Accept': 'text/event-stream', 'Cache-Control': 'no-cache'},
        stream=True)

@pytest.mark.usefixtures("unicode_multibyte_responses")
def test_multiple_messages():
    c = sseclient.SSEClient('http://blah.com',chunk_size=51)
    assert next(c).data == 'ööööööööööööööööööööööööööööööööööööööööööööööööööööööööö'
    assert next(c).data == 'äääääääääääääääääääääääääääääääääääääääääääääääääääääääää'
    assert next(c).data == 'üüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüüü'

def test_event_stream():
    """Check whether event.data can be loaded."""
    limit = 50
    url = 'https://stream.wikimedia.org/v2/stream/recentchange'
    source = sseclient.SSEClient(url)
    for n, event in enumerate(source, start=1):
        if event.event != 'message' or not event.data:
            continue
        try:
            element = json.loads(event.data)
        except ValueError as e:
            source.resp.close()
            raise e
        if n == limit:
            break
    assert True

if __name__ == '__main__':
    try:
        pytest.main()
    except SystemExit:
        pass
