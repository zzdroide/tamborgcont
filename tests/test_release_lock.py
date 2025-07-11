import pytest

from hook.constants import RC, Paths
from hook.main import check_repo, main


class TestReleaseLock:
    @pytest.fixture(autouse=True)
    def set_pam_vars(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'close_session')

    @pytest.fixture
    def locked_repo(self):
        assert not Paths.repo_is_ok.is_file()
        Paths.lock.mkdir()

    def run_main(self):
        main(['main.py', 'pam'])

    @pytest.mark.usefixtures('locked_repo')
    def test_check_repo_ok_effect(self, monkeypatch):
        monkeypatch.setattr('hook.main.check_repo', lambda: (True, ''))

        self.run_main()

        assert Paths.repo_is_ok.is_file()
        assert not Paths.lock.is_dir()

    @pytest.mark.usefixtures('locked_repo')
    def test_check_repo_nok_effect(self, monkeypatch):
        monkeypatch.setattr('hook.main.check_repo', lambda: (False, ''))

        with pytest.raises(SystemExit) as e:
            self.run_main()
        assert e.value.code == RC.generic_error

        assert not Paths.repo_is_ok.is_file()
        assert Paths.lock.is_dir()    # Keep data to diagnose later

    @pytest.fixture
    def locked_by_user1(self, locked_repo):  # noqa: ARG002
        Paths.lock_user.write_text('user1')

    def arcs2str(self, arcs):
        lines = (f'{arc[0]}\x00{arc[1]}' for arc in arcs)
        return '\x00'.join(lines) + '\x00'

    def write_prev_arcs(self, arcs):
        Paths.lock_prev_arcs.write_text(self.arcs2str(arcs))

    def prev_were_modified(self):
        return check_repo() == (False, 'Previous archives were modified!')

    @pytest.mark.usefixtures('locked_by_user1')
    def test_check_modified_arcs(self, monkeypatch):
        self.write_prev_arcs((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        ))

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: '')
        assert self.prev_were_modified()

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert self.prev_were_modified()

    @pytest.mark.usefixtures('locked_by_user1')
    def test_check_new_prefix(self, monkeypatch):
        self.write_prev_arcs((
            ('id1', 'user1-asdf'),
        ))

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
        )))
        assert check_repo()[0]

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
        )))
        assert check_repo()[0]

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert check_repo()[0]

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
        )))
        assert not check_repo()[0]

        monkeypatch.setattr('hook.borg.dump_arcs', lambda: self.arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user2-asdf'),
            ('id4', 'user1-asdf'),
        )))
        assert not check_repo()[0]
