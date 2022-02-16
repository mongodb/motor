"""Gratefully adapted from aiohttp, provides coroutine support to autodoc."""

from sphinx import addnodes
from sphinx.domains.python import PyFunction, PyMethod


class PyCoroutineMixin(object):
    def handle_signature(self, sig, signode):
        ret = super().handle_signature(sig, signode)
        signode.insert(0, addnodes.desc_annotation("coroutine ", "coroutine "))
        return ret


class PyCoroutineFunction(PyCoroutineMixin, PyFunction):
    def run(self):
        self.name = "py:function"
        return PyFunction.run(self)


class PyCoroutineMethod(PyCoroutineMixin, PyMethod):
    def run(self):
        self.name = "py:method"
        return PyMethod.run(self)


def setup(app):
    app.add_directive_to_domain("py", "coroutinefunction", PyCoroutineFunction)
    app.add_directive_to_domain("py", "coroutinemethod", PyCoroutineMethod)
    return {"version": "1.0", "parallel_read_safe": True}
