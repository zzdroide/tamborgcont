import os

import pytest

from hook.constants import RC, Paths
from hook.main import main


class TestFillLock:
    @pytest.fixture(autouse=True)
    def already_locked(self):
        os.mkdir(Paths.lock)

    @pytest.fixture()
    def known_user(self, monkeypatch):
        monkeypatch.setattr('hook.main.does_user_exist', lambda u: True)

    @pytest.fixture()
    def unknown_user(self, monkeypatch):
        monkeypatch.setattr('hook.main.does_user_exist', lambda u: False)

    def run_main(self):
        main(['main.py', 'ssh_command', 'user'])

    def test_deny_unknown_user(self, unknown_user):
        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.access_denied

    def test_fills(self, monkeypatch, known_user):
        monkeypatch.setattr('hook.Borg.dump_arcs', lambda: 'archives')

        self.run_main()

        with open(Paths.lock_user, 'r') as f:
            assert f.read() == 'user'
        with open(Paths.lock_prev_arcs, 'r') as f:
            assert f.read() == 'archives'
