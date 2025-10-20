import pytest

from hook.constants import RC, Paths
from hook.main import main
from shared import borg


class TestAcquireLock:
    @pytest.fixture(autouse=True)
    def pam_type_open_session(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'open_session')

    @pytest.fixture
    def borg_repo_locked(self, monkeypatch):
        monkeypatch.setattr(borg, 'is_repo_unlocked', lambda _: False)

    @pytest.fixture
    def borg_repo_unlocked(self, monkeypatch):
        monkeypatch.setattr(borg, 'is_repo_unlocked', lambda _: True)

    def run_main(self):
        main(['main.py', 'pam'])

    def test_deny_on_repo_disabled(self):
        Paths.repo_enabled.unlink()

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('borg_repo_locked')
    def test_deny_on_locked_borg(self):
        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('borg_repo_unlocked')
    def test_deny_on_locked_state(self):
        Paths.lock.mkdir()
        Paths.lock_user.write_text('TAM_2009')

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('borg_repo_unlocked')
    def test_lock_contents(self, monkeypatch):
        monkeypatch.setattr(borg, 'dump_arcs', lambda _: 'archives')

        self.run_main()

        assert Paths.lock_user.read_text() == 'TAM_2009'
        assert Paths.lock_prev_arcs.read_text() == 'archives'
