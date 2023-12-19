import os
import tempfile
from inspect import isclass

import pytest
import sh

from hook import Borg
from hook.constants import Paths


@pytest.fixture(autouse=True)
def default_state():
    with tempfile.TemporaryDirectory() as newpath:
        old_cwd = os.getcwd()
        os.chdir(newpath)
        os.mkdir(Paths.state)
        yield
        os.chdir(old_cwd)


@pytest.fixture(autouse=True)
def no_local_config(monkeypatch):
    def prevent_call(*args, **kwargs):
        raise Exception('Prevented local config usage')
    monkeypatch.setattr('hook.config.get_config', prevent_call)


class PreventSh:
    def __getattr__(self, name):
        try:
            attr = getattr(sh, name)
        except sh.CommandNotFound:
            attr = None

        if isclass(attr) and issubclass(attr, Exception):
            return attr
        else:
            return self

    def __call__(self, *args):
        raise Exception('Prevented sh call')


@pytest.fixture(autouse=True)
def no_sh_calls(monkeypatch):
    monkeypatch.setattr(Borg, 'sh', PreventSh())
