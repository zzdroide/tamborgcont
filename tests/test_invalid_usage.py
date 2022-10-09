import pytest

from src.hook import main


def test_no_hook_src():
    with pytest.raises(SystemExit) as e:
        main(['hook.py'])
    assert e.value.code == 2


def test_invalid_hook_src():
    with pytest.raises(SystemExit) as e:
        main(['hook.py', 'asdf'])
    assert e.value.code == 2


def test_no_pam_type(monkeypatch):
    monkeypatch.delenv('PAM_TYPE', raising=False)
    with pytest.raises(SystemExit) as e:
        main(['hook.py', 'pam'])
    assert e.value.code == 2


def test_invalid_pam_type(monkeypatch):
    monkeypatch.setenv('PAM_TYPE', 'asdf')
    with pytest.raises(SystemExit) as e:
        main(['hook.py', 'pam'])
    assert e.value.code == 2


def test_no_ssh_command_key_user():
    with pytest.raises(SystemExit) as e:
        main(['hook.py', 'ssh_command'])
    assert e.value.code == 2
