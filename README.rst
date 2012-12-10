=================
Python SSE Client
=================

This is a Python client library for iterating over http Server Sent Event (SSE)
streams.  The SSEClient class accepts a url on init, and is then an iterator
over messages coming from the server.

Installation
------------

Use pip::

    pip install sseclient

Usage
-----

::
    
    from sseclient import SSEClient

    messages = SSEClient('http://mysite.com/sse_stream/')
    for msg in messages:
        do_something_useful(msg)

Each message object will have a 'data' attribute, as well as optional 'event',
'id', and 'retry' attributes.

Optional init parameters:

- last_id: If provided, this parameter will be sent to the server to tell it to
  return only messages more recent than this ID.

- retry: Number of milliseconds to wait after disconnects before attempting to
  reconnect.  The server may change this by including a 'retry' line in a
  message.  Retries are handled automatically by the SSEClient object.

You may also provide any additional keyword arguments supported by the
Requests_ library, such as a 'headers' dict and a (username, password) tuple
for 'auth'.

Development
-----------

Install the test dependencies::

    pip install pytest mock

And run the tests::

    $ py.test
    ================== test session starts ===================
    platform linux2 -- Python 2.7.3 -- pytest-2.3.4
    collected 9 items 

    test_sseclient.py .........

    ================ 9 passed in 0.31 seconds ================

There are a couple TODO items in the code for getting the implementation
completely in line with the finer points of the SSE spec.

Additional Resources
--------------------

- `HTML5Rocks Tutorial`_
- `Official SSE Spec`_

.. _Requests: http://docs.python-requests.org/en/latest/
.. _HTML5Rocks Tutorial: http://www.html5rocks.com/en/tutorials/eventsource/basics/
.. _Official SSE Spec: http://www.whatwg.org/specs/web-apps/current-work/multipage/comms.html#server-sent-events

