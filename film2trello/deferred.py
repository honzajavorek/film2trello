# -*- coding: utf-8 -*-
# Concept from http://flask.pocoo.org/docs/0.10/patterns/deferredcallbacks/


from flask import g


def after_this_request(f):
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(f)
    return f


def call_after_request_callbacks(response):
    for callback in getattr(g, 'after_request_callbacks', ()):
        callback(response)
    return response
