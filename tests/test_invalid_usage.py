import pytest

from src.constants import RC
from src.hook import main


class TestInvalidUsage:
    def test_no_hook_src(self):
        with pytest.raises(SystemExit) as e:
            main(['hook.py'])
        assert e.value.code == RC.invalid_usage

    def test_invalid_hook_src(self):
        with pytest.raises(SystemExit) as e:
            main(['hook.py', 'asdf'])
        assert e.value.code == RC.invalid_usage

    def test_no_pam_type(self, monkeypatch):
        monkeypatch.delenv('PAM_TYPE', raising=False)
        with pytest.raises(SystemExit) as e:
            main(['hook.py', 'pam'])
        assert e.value.code == RC.invalid_usage

    def test_invalid_pam_type(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'asdf')
        with pytest.raises(SystemExit) as e:
            main(['hook.py', 'pam'])
        assert e.value.code == RC.invalid_usage

    def test_no_ssh_command_key_user(self):
        with pytest.raises(SystemExit) as e:
            main(['hook.py', 'ssh_command'])
        assert e.value.code == RC.invalid_usage
