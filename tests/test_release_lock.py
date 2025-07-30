import pytest

import hook
from hook import main
from hook.constants import RC, Paths
from hook.utils import BadRepoError, arcs2str


class TestReleaseLock:
    @pytest.fixture(autouse=True)
    def pam_type_close_session(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'close_session')

    @pytest.fixture
    def locked_repo(self):
        Paths.lock.mkdir()

    @pytest.mark.usefixtures('locked_repo')
    def test_pam_check_repo_ok_effect(self, monkeypatch):
        monkeypatch.setattr(main, 'check_repo', lambda _repo, _user: None)
        main.main(['main.py', 'pam'])
        assert not Paths.lock.is_dir()

    @pytest.mark.usefixtures('locked_repo')
    def test_restart_check_repo_ok_effect(self, monkeypatch):
        monkeypatch.setattr(main, 'check_repo', lambda *_args, **_kwargs: None)
        main.main(['main.py', 'tamborg-release-lock'])
        assert not Paths.lock.is_dir()

    @pytest.mark.usefixtures('locked_repo')
    def test_check_repo_nok_effect(self, monkeypatch):
        def raise_badrepoerror(*_args, **_kwargs):
            raise BadRepoError
        monkeypatch.setattr(main, 'check_repo', raise_badrepoerror)

        with pytest.raises(SystemExit) as e:
            main.main(['main.py', 'pam'])
        assert e.value.code == RC.generic_error
        assert Paths.lock.is_dir()

        main.main(['main.py', 'tamborg-release-lock'])
        Paths.set_repo_name('TAM')
        assert Paths.lock.is_dir()

    @pytest.fixture
    def locked_by_user1(self, monkeypatch, locked_repo):  # noqa: ARG002
        Paths.lock_user.write_text('user1')
        monkeypatch.setattr(hook.config, 'get_from_pk', lambda _: ('TAM', 'user1'))

    def write_prev_arcs(self, arcs):
        Paths.lock_prev_arcs.write_text(arcs2str(arcs))

    def check_repo(self):
        main.check_repo('TAM', 'user1')

    @pytest.mark.usefixtures('locked_by_user1')
    def test_allow_self_temp_delete(self, monkeypatch):
        self.write_prev_arcs((
            ('id1', 'user1-asdf'),
            ('id2', 'user1[temp]'),
        ))

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
        )))
        self.check_repo()

    def assert_prev_were_modified(self):
        with pytest.raises(BadRepoError) as e:
            self.check_repo()
        assert e.value.args[0] == 'Previous archives were modified!'

    def assert_bad_new_archive(self):
        with pytest.raises(BadRepoError) as e:
            self.check_repo()
        assert "] that doesn't start with [" in e.value.args[0]

    @pytest.mark.usefixtures('locked_by_user1')
    def test_check_modified_arcs(self, monkeypatch):
        self.write_prev_arcs((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        ))

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: '')
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id0', 'user0[temp]'),
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

    @pytest.mark.usefixtures('locked_by_user1')
    def test_check_new_prefix(self, monkeypatch):
        self.write_prev_arcs((
            ('id1', 'user1-asdf'),
        ))

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
        )))
        self.check_repo()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1[temp]'),
        )))
        self.check_repo()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2[temp]'),
        )))
        self.assert_bad_new_archive()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
        )))
        self.check_repo()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.check_repo()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
        )))
        self.assert_bad_new_archive()

        monkeypatch.setattr(hook.borg, 'dump_arcs', lambda _: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user2-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_bad_new_archive()
