import pytest

from hook.constants import RC, Paths
from hook.main import main


class TestFillLock:
    @pytest.fixture(autouse=True)
    def already_locked(self):
        Paths.lock.mkdir()

    @pytest.fixture
    def known_user(self, monkeypatch):
        monkeypatch.setattr('hook.main.does_user_exist', lambda _: True)

    @pytest.fixture
    def unknown_user(self, monkeypatch):
        monkeypatch.setattr('hook.main.does_user_exist', lambda _: False)

    def run_main(self):
        main(['main.py', 'ssh_command', 'user'])

    @pytest.mark.usefixtures('unknown_user')
    def test_deny_unknown_user(self):
        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    @pytest.mark.usefixtures('known_user')
    def test_fills(self, monkeypatch):
        monkeypatch.setattr('hook.borg.dump_arcs', lambda: 'archives')

        self.run_main()

        assert Paths.lock_user.read_text() == 'user'
        assert Paths.lock_prev_arcs.read_text() == 'archives'
