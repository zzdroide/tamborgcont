import os

import pytest

from hook.constants import RC, Paths
from hook.main import main
from hook.utils import mkfile


class TestAcquireLock:
    @pytest.fixture(autouse=True)
    def set_pam_vars(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'open_session')
        monkeypatch.setenv('PAM_RHOST', '192.168.0.100')

    @pytest.fixture()
    def borg_repo_locked(self, monkeypatch):
        monkeypatch.setattr('hook.Borg.is_repo_unlocked', lambda: False)

    @pytest.fixture()
    def borg_repo_unlocked(self, monkeypatch):
        monkeypatch.setattr('hook.Borg.is_repo_unlocked', lambda: True)

    def run_main(self):
        main(['main.py', 'pam'])

    def test_deny_on_reponok(self):
        assert not os.path.isfile(Paths.repo_is_ok)

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    def test_deny_on_locked_repo(self, borg_repo_locked):
        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    def test_deny_on_locked(self, borg_repo_unlocked):
        os.mkdir(Paths.lock)
        with open(Paths.lock_ip, 'x') as f:
            f.write(os.environ.get('PAM_RHOST'))

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    def test_write_ip(self, borg_repo_unlocked):
        mkfile(Paths.repo_is_ok)
        self.run_main()
        with open(Paths.lock_ip, 'r') as f:
            assert f.read() == '192.168.0.100'
