import logging
import os
import tempfile
from inspect import isclass
from pathlib import Path

import pytest
import sh

from hook import borg, utils
from hook.constants import Paths


@pytest.fixture(autouse=True)
def default_state():
    with tempfile.TemporaryDirectory() as newpath:
        old_cwd = Path.cwd()
        os.chdir(newpath)
        Paths.state.mkdir()
        yield
        os.chdir(old_cwd)


@pytest.fixture(autouse=True)
def no_local_config(monkeypatch):
    def prevent_call(*_args, **_kwargs):
        msg = 'Prevented local config usage'
        raise Exception(msg)
    monkeypatch.setattr('hook.config.get_config', prevent_call)


class PreventSh:
    def __getattr__(self, name):
        try:
            attr = getattr(sh, name)
        except sh.CommandNotFound:
            attr = None

        if isclass(attr) and issubclass(attr, Exception):
            return attr
        return self

    def __call__(self, *_args):
        msg = 'Prevented sh call'
        raise Exception(msg)


@pytest.fixture(autouse=True)
def no_sh_calls(monkeypatch):
    monkeypatch.setattr(borg, 'sh', PreventSh())


@pytest.fixture(autouse=True)
def disable_logger(monkeypatch):
    def get_logger():
        logger = logging.getLogger()
        logger.disabled = True
        return logger
    monkeypatch.setattr(utils, 'get_logger', get_logger)
