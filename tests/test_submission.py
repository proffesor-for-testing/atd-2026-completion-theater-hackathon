"""Committed-source intake preserves exact bytes and rejects unsafe inputs."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import submission


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.app = self.repo / 'app'
        self.app.mkdir()
        (self.app / 'main.py').write_bytes(b'print("frozen")\n')
        (self.app / 'README.md').write_text('Run main.py\n')
        (self.repo / '.gitattributes').write_text('app/README.md export-ignore\n')
        self.sha = self.commit()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'Fixture source')
        return self.git('rev-parse', 'HEAD')

    def test_reads_frozen_blobs_not_workspace_or_export_attributes(self):
        (self.app / 'main.py').write_text('print("late repair")\n')
        (self.app / 'untracked.py').write_text('not submitted\n')
        archive = self.root / 'retained.zip'
        result = submission.create(self.repo, self.sha, 'app', archive)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read('main.py'), b'print("frozen")\n')
            self.assertIn('README.md', z.namelist())
            self.assertNotIn('untracked.py', z.namelist())
        self.assertEqual(result['commit'], self.sha)
        self.assertEqual(result['appPath'], 'app')
        self.assertEqual(result['sourceId'], submission.snapshot.check(archive)['sourceId'])
        with self.assertRaises(FileExistsError):
            submission.create(self.repo, self.sha, 'app', archive)

    def test_preserves_case_distinct_git_names_without_host_normalization(self):
        blob = subprocess.run(['git', '-C', str(self.repo), 'hash-object', '-w', '--stdin'],
                              input=b'UPPERCASE', check=True, stdout=subprocess.PIPE).stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', '100644', blob, 'app/MAIN.py')
        self.git('commit', '-qm', 'Case-distinct fixture')
        archive = self.root / 'case.zip'
        submission.create(self.repo, self.git('rev-parse', 'HEAD'), 'app', archive)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(z.read('MAIN.py'), b'UPPERCASE')
            self.assertEqual(z.read('main.py'), b'print("frozen")\n')

    def test_exclusions_and_later_commit_do_not_replace_frozen_identity(self):
        (self.app / '.env').write_text('fixture-only-secret\n')
        (self.app / '.env.example').write_text('SETTING=\n')
        (self.app / 'main.py').write_text('print("new")\n')
        newer = self.commit()
        old = submission.create(self.repo, self.sha, 'app', self.root / 'old.zip')
        new = submission.create(self.repo, newer, 'app', self.root / 'new.zip')
        self.assertNotEqual(old['sourceId'], new['sourceId'])
        with zipfile.ZipFile(self.root / 'new.zip') as z:
            self.assertNotIn('.env', z.namelist())
            self.assertIn('.env.example', z.namelist())

    def test_refuses_moving_refs_short_hashes_unsafe_paths_and_missing_app(self):
        for ref in ('HEAD', self.sha[:8], '--help'):
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, 'full'):
                submission.create(self.repo, ref, 'app', self.root / 'bad.zip')
        for path in ('', '.', '../app', '/app', 'app/../app', 'app\\file', 'C:app', 'app/'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'relative'):
                submission.create(self.repo, self.sha, path, self.root / 'bad.zip')
        with self.assertRaisesRegex(ValueError, 'Empty source'):
            submission.create(self.repo, self.sha, 'missing', self.root / 'bad.zip')
        self.assertFalse((self.root / 'bad.zip').exists())
        with self.assertRaisesRegex(ValueError, 'outside'):
            submission.create(self.repo, self.sha, 'app', self.app / 'source.zip')

    def test_refuses_committed_symlink_and_submodule_without_executing(self):
        # Direct index entries work on Windows too, without symlink privileges.
        blob = subprocess.run(['git', '-C', str(self.repo), 'hash-object', '-w', '--stdin'],
                              input=b'/private/outside', check=True, stdout=subprocess.PIPE).stdout.decode().strip()
        self.git('update-index', '--add', '--cacheinfo', '120000', blob, 'app/link')
        self.git('commit', '-qm', 'Fixture symlink')
        link_sha = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(ValueError, 'Symlink/submodule'):
            submission.create(self.repo, link_sha, 'app', self.root / 'bad.zip')
        self.git('update-index', '--force-remove', 'app/link')
        self.git('update-index', '--add', '--cacheinfo', '160000', self.sha, 'app/submodule')
        self.git('commit', '-qm', 'Fixture submodule')
        with self.assertRaisesRegex(ValueError, 'Symlink/submodule'):
            submission.create(self.repo, self.git('rev-parse', 'HEAD'), 'app', self.root / 'bad.zip')
        self.assertFalse((self.root / 'bad.zip').exists())


if __name__ == '__main__':
    unittest.main()
