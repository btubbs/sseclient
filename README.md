# Filigran Python SSE Client

This is a Python client library for iterating over http Server Sent Event (SSE)
streams (also known as EventSource, after the name of the Javascript interface
inside browsers).  The SSEClient class accepts a url on init, and is then an
iterator over messages coming from the server.

Forked from btubbs/sseclient to mainly support chunk stream messages, thanks to @ristowee