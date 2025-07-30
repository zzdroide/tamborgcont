import pytest

from hook.constants import RC
from hook.main import main


class TestInvalidUsage:
    def test_invalid_hook_src(self):
        with pytest.raises(SystemExit) as e:
            main(['main.py'])
        assert e.value.code == RC.invalid_usage

        with pytest.raises(SystemExit) as e:
            main(['main.py', 'asdf'])
        assert e.value.code == RC.invalid_usage

    def check_invalid_pam_usage(self):
        with pytest.raises(SystemExit) as e:
            main(['main.py', 'pam'])
        assert e.value.code == RC.invalid_usage

    def test_bad_ssh_auth_info(self, monkeypatch):
        monkeypatch.delenv('SSH_AUTH_INFO_0')
        self.check_invalid_pam_usage()
        monkeypatch.setenv('SSH_AUTH_INFO_0', 'publickey asdf')
        self.check_invalid_pam_usage()
        monkeypatch.setenv('SSH_AUTH_INFO_0', 'publickey ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI/does+not+exist')
        self.check_invalid_pam_usage()

    def test_bad_pam_type(self, monkeypatch):
        self.check_invalid_pam_usage()
        monkeypatch.setenv('PAM_TYPE', '')
        self.check_invalid_pam_usage()
        monkeypatch.setenv('PAM_TYPE', 'asdf')
        self.check_invalid_pam_usage()
