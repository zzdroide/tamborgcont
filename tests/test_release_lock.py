import pytest

from hook.main import Hook, main
from hook.utils import BadRepoError, arcs2str
from shared import config
from shared.borg import Borg
from shared.constants import RC, Paths


class TestReleaseLock:
    @pytest.fixture(autouse=True)
    def pam_type_close_session(self, monkeypatch):
        monkeypatch.setenv('PAM_TYPE', 'close_session')

    @pytest.fixture
    def locked_repo(self, paths: Paths):
        paths.lock.mkdir()

    @pytest.mark.usefixtures('locked_repo')
    def test_pam_check_repo_ok_effect(self, monkeypatch, paths: Paths):
        monkeypatch.setattr(Hook, 'check_repo', lambda _self, _user: None)
        main(['main.py', 'pam'])
        assert not paths.lock.is_dir()

    @pytest.mark.usefixtures('locked_repo')
    def test_restart_check_repo_ok_effect(self, monkeypatch, paths: Paths):
        monkeypatch.setattr(Hook, 'check_repo', lambda *_args, **_kwargs: None)
        main(['main.py', 'tamborg-release-lock'])
        assert not paths.lock.is_dir()

    @pytest.mark.usefixtures('locked_repo')
    def test_check_repo_nok_effect(self, monkeypatch, paths: Paths):
        def raise_badrepoerror(_self, _user):
            raise BadRepoError
        monkeypatch.setattr(Hook, 'check_repo', raise_badrepoerror)

        with pytest.raises(SystemExit) as e:
            main(['main.py', 'pam'])
        assert e.value.code == RC.generic_error
        assert paths.lock.is_dir()

        main(['main.py', 'tamborg-release-lock'])
        assert paths.lock.is_dir()

    @pytest.fixture
    def locked_by_user1(self, monkeypatch, locked_repo, paths: Paths):  # noqa: ARG002
        paths.lock_user.write_text('user1')
        monkeypatch.setattr(config, 'get_config_from_pk', lambda _: ('TAM', 'user1'))

    def write_prev_arcs(self, paths: Paths, arcs):
        paths.lock_prev_arcs.write_text(arcs2str(arcs))

    def check_repo(self):
        hook = Hook('TAM')
        hook.check_repo('user1')

    @pytest.mark.usefixtures('locked_by_user1')
    def test_allow_first_temp_rename(self, monkeypatch, paths: Paths):
        self.write_prev_arcs(paths, (
            ('id1', 'user1(temp)-2026-01-01'),
        ))

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id2', 'user1-asdf'),
        )))
        self.check_repo()

    @pytest.mark.usefixtures('locked_by_user1')
    def test_allow_self_temp_delete(self, monkeypatch, paths: Paths):
        self.write_prev_arcs(paths, (
            ('id1', 'user1-asdf'),
            ('id2', 'user1(temp)-2026-01-01'),
        ))

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
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
    def test_check_modified_arcs(self, monkeypatch, paths: Paths):
        self.write_prev_arcs(paths, (
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        ))

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: '')
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id0', 'user2-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id0', 'user0(temp)-2026-01-01'),
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdg'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
            ('id3', 'user1-asdf'),
        )))
        self.assert_prev_were_modified()

    @pytest.mark.usefixtures('locked_by_user1')
    def test_check_new_prefix(self, monkeypatch, paths: Paths):
        self.write_prev_arcs(paths, (
            ('id1', 'user1-asdf'),
        ))

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
        )))
        self.check_repo()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1(temp)-2026-01-01'),
        )))
        self.check_repo()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2(temp)-2026-01-01'),
        )))
        self.assert_bad_new_archive()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
        )))
        self.check_repo()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user1-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.check_repo()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user2-asdf'),
        )))
        self.assert_bad_new_archive()

        monkeypatch.setattr(Borg, 'dump_arcs', lambda _self: arcs2str((
            ('id1', 'user1-asdf'),
            ('id2', 'user1-asdf'),
            ('id3', 'user2-asdf'),
            ('id4', 'user1-asdf'),
        )))
        self.assert_bad_new_archive()
