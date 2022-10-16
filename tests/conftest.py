import os
import tempfile

import pytest
import sh

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
def no_sh_calls(monkeypatch):
    def prevent_call(*args, **kwargs):
        raise Exception('Prevented sh call')
    monkeypatch.setattr(sh.RunningCommand, '__init__', prevent_call)


@pytest.fixture(autouse=True)
def no_local_config(monkeypatch):
    def prevent_call(*args, **kwargs):
        raise Exception('Prevented local config usage')
    monkeypatch.setattr('hook.config.get_config', prevent_call)
