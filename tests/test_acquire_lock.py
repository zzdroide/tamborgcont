import pytest

import hook
from hook.main import main
from shared.borg import Borg
from shared.constants import RC, Paths


class TestAcquireLock:
    @pytest.fixture(autouse=True)
    def pam_type_open_session(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'open_session')

    @pytest.fixture(autouse=True)
    def dump_dummy_arcs(self, monkeypatch):
        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: 'dummy_archives')

    @pytest.fixture
    def borg_repo_locked(self, monkeypatch):
        monkeypatch.setattr(Borg, 'is_repo_unlocked', lambda _self: False)

    @pytest.fixture
    def borg_repo_unlocked(self, monkeypatch):
        monkeypatch.setattr(Borg, 'is_repo_unlocked', lambda _self: True)

    def run_main(self):
        main(['main.py', 'pam'])

    def test_deny_on_repo_disabled(self, paths: Paths):
        paths.repo_enabled.unlink()

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    def test_deny_on_waiting_for_other(self, monkeypatch):
        monkeypatch.setattr(hook.utils, 'get_waiting_for', lambda _repo: 'other')
        monkeypatch.setattr(hook.main, 'get_waiting_for', lambda _repo: 'other')

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('borg_repo_unlocked')
    def test_allow_when_waiting_for_me(self, monkeypatch):
        monkeypatch.setattr(hook.utils, 'get_waiting_for', lambda _repo: 'TAM_2009')
        monkeypatch.setattr(hook.main, 'get_waiting_for', lambda _repo: 'TAM_2009')

        self.run_main()     # Should not raise

    @pytest.mark.usefixtures('borg_repo_locked')
    def test_deny_on_locked_borg(self):
        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('borg_repo_unlocked')
    def test_deny_on_locked_state(self, paths: Paths):
        paths.lock.mkdir()
        paths.lock_user.write_text('TAM_2009')

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('borg_repo_unlocked')
    def test_lock_contents(self, paths: Paths):
        self.run_main()

        assert paths.lock_user.read_text() == 'TAM_2009'
        assert paths.lock_prev_arcs.read_text() == 'dummy_archives'
