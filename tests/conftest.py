import logging
import os
import tempfile
from inspect import isclass
from pathlib import Path

import pytest
import sh
import yaml
from tenacity import wait_fixed

import hook
from shared import borg, config
from shared.constants import Paths


def mkfile(path: Path):
    path.open('x').close()


@pytest.fixture(autouse=True)
def use_test_config(monkeypatch):
    with Path('./config.test.yml').open(encoding='utf-8') as f:
        test_config = yaml.safe_load(f)

    monkeypatch.setattr(config, 'get_config', lambda: test_config)


@pytest.fixture
def paths():
    return Paths('TAM')


@pytest.fixture(autouse=True)
def default_state(
    monkeypatch,
    use_test_config,  # Load with relative path before chdir  # noqa: ARG001
    paths: Paths,
):
    with tempfile.TemporaryDirectory() as newpath:
        old_cwd = Path.cwd()
        os.chdir(newpath)
        paths.repo_state.mkdir(parents=True)
        mkfile(paths.repo_enabled)
        monkeypatch.setenv('SSH_AUTH_INFO_0', 'publickey ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEEzh7eIUFgJy/CLTHN+B0wlq3QK0aTZz/0FVfKCtdA0\n')
        yield
        os.chdir(old_cwd)


class PreventSh:
    def __getattr__(self, name):
        try:
            attr = getattr(sh, name)
        except sh.CommandNotFound:
            attr = None

        if isclass(attr) and issubclass(attr, Exception):
            return attr
        return self

    def __call__(self, *_args, **_kwargs):
        msg = 'Prevented sh call'
        raise Exception(msg)


@pytest.fixture(autouse=True)
def no_sh_calls(monkeypatch):
    monkeypatch.setattr(borg, 'sh', PreventSh())


@pytest.fixture(autouse=True)
def disable_logger():
    logger = logging.getLogger()
    logger.handlers.clear()
    # Logs are still captured by `pytest -rA`


@pytest.fixture(autouse=True)
def tenacity_zero_wait(monkeypatch):
    monkeypatch.setattr(wait_fixed, '__call__', lambda _self, _: 0)


@pytest.fixture(autouse=True)
def none_waiting_for(monkeypatch):
    monkeypatch.setattr(hook.utils, 'get_waiting_for', lambda _repo: None)
    monkeypatch.setattr(hook.main, 'get_waiting_for', lambda _repo: None)
