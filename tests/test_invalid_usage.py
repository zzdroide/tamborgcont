import pytest

from hook.constants import RC
from hook.main import main


class TestInvalidUsage:
    def test_no_hook_src(self):
        with pytest.raises(SystemExit) as e:
            main(['main.py'])
        assert e.value.code == RC.invalid_usage

    def test_invalid_hook_src(self):
        with pytest.raises(SystemExit) as e:
            main(['main.py', 'asdf'])
        assert e.value.code == RC.invalid_usage

    def test_no_pam_type(self, monkeypatch):
        monkeypatch.delenv('PAM_TYPE', raising=False)
        with pytest.raises(SystemExit) as e:
            main(['main.py', 'pam'])
        assert e.value.code == RC.invalid_usage

    def test_invalid_pam_type(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'asdf')
        with pytest.raises(SystemExit) as e:
            main(['main.py', 'pam'])
        assert e.value.code == RC.invalid_usage

    def test_no_ssh_command_key_user(self):
        with pytest.raises(SystemExit) as e:
            main(['main.py', 'ssh_command'])
        assert e.value.code == RC.invalid_usage
