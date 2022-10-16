import os

import pytest

from src.constants import RC, Paths
from src.hook import main, check_repo


class TestReleaseLock:
    @pytest.fixture(autouse=True)
    def set_pam_vars(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'close_session')

    @pytest.fixture()
    def locked_repo(self):
        assert not os.path.isfile(Paths.repo_is_ok)
        os.mkdir(Paths.lock)

    def run_main(self):
        main(['hook.py', 'pam'])

    def test_check_repo_ok_effect(self, monkeypatch, locked_repo):
        monkeypatch.setattr('src.hook.check_repo', lambda: (True, ''))

        self.run_main()

        assert os.path.isfile(Paths.repo_is_ok)
        assert not os.path.isdir(Paths.lock)

    def test_check_repo_nok_effect(self, monkeypatch, locked_repo):
        monkeypatch.setattr('src.hook.check_repo', lambda: (False, ''))

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.generic_error

        assert not os.path.isfile(Paths.repo_is_ok)
        assert os.path.isdir(Paths.lock)    # Keep data to diagnose later

    @pytest.fixture()
    def locked_by_user1(self, locked_repo):
        with open(Paths.lock_user, 'x') as f:
            f.write('user1')

    def arcs2str(self, arcs):
        lines = (f'{arc[0]}\x00{arc[1]}' for arc in arcs)
        return '\x00'.join(lines) + '\x00'

    def write_prev_arcs(self, arcs):
        with open(Paths.lock_prev_arcs, 'w') as f:
            f.write(self.arcs2str(arcs))

    def prev_were_modified(self):
        return check_repo() == (False, 'Previous archives were modified!')

    def test_check_modified_arcs(self, monkeypatch, locked_by_user1):
        self.write_prev_arcs((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        ))

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: '')
        assert self.prev_were_modified()

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

    def test_check_new_prefix(self, monkeypatch, locked_by_user1):
        self.write_prev_arcs((
            ('id1', 'user1-asdf'),
        ))

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
        )))
        assert check_repo()[0]

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
        )))
        assert check_repo()[0]

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert check_repo()[0]

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
        )))
        assert not check_repo()[0]

        monkeypatch.setattr('src.Borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user2-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert not check_repo()[0]
