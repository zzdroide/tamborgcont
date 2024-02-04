'''
Ensure that a failure to execute borg (can be simulated with ssh -N ...)
won't lock the repo as not-OK.
'''

from hook.constants import Paths
from hook.main import main
from hook.utils import mkfile


def run_open(monkeypatch):
    monkeypatch.setenv('PAM_TYPE', 'open_session')
    main(['main.py', 'pam'])


def run_close(monkeypatch):
    monkeypatch.setenv('PAM_TYPE', 'close_session')
    main(['main.py', 'pam'])


def test_ssh_without_command(monkeypatch):
    mkfile(Paths.repo_is_ok)
    monkeypatch.setattr('hook.Borg.is_repo_unlocked', lambda: True)
    monkeypatch.setenv('PAM_RHOST', '192.168.0.100')

    run_open(monkeypatch)
    run_close(monkeypatch)
    run_open(monkeypatch)
    run_close(monkeypatch)
