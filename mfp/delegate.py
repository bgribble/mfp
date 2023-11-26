#! /usr/bin/env python
"""
delegate.py -- helper for delegating methods to a backend

A "backend" that is being delegated to should inherit
from DelegateMixin.

Methods in the backend decorated with @delegatemethod
will be available on the frontend object passed as a
constructor arg to the backend.

If the Backend interface is abstract (which is to be expected)
the @delegatemethod decorator can be put on the interface class

    class BackendInterface(ABC, DelegateMixin):
        @abstractmethod
        @delegatemethod
        def m1(self):
            pass

    class Backend (BackendInterface):
        def m1(self):
            print("hello, world")

    class Frontend:
        def __init__(self):
            self.backend = Backend(self)

    f = Frontend()
    f.m1() --> "hello, world"

"""

class delegatemethod:
    def __init__(self, func):
        self.func = func

    def __set_name__(self, owner, name):
        if not hasattr(owner, 'delegated_methods'):
            owner.delegated_methods = []
        owner.delegated_methods.append(name)
        setattr(owner, name, self.func)


class DelegateMixin:
    reversed_attrs = []

    def __init__(self, delegator):
        self.wrapper = delegator
        for attr in self.delegated_methods:
            setattr(delegator, attr, self._delegate_helper(attr))

        for attr in self.reversed_attrs:
            setattr(type(self), attr, property(self._reverse_delegate_helper(attr)))

    def _delegate_helper(self, attr):
        thunk = getattr(self, attr)
        def inner(*args, **kwargs):
            return thunk(*args, **kwargs)
        return inner

    def _reverse_delegate_helper(self, attr):
        def inner(*args, **kwargs):
            return getattr(self.wrapper, attr)
        return inner
