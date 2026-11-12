"""使用伪造 Release 与 API 回执，默认测试不访问 GitHub、不写远程文件。"""
import base64
from contextlib import redirect_stdout
from io import BytesIO, StringIO
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError

import update_changelog as changelog

REPO = 'example/releases'


def release(tag='v0.1.3', body='- 自动测速\r\n- 自动换源', **kwargs):
    return {'tag_name': tag, 'body': body, 'draft': False, 'prerelease': False,
            'published_at': '2026-11-12T18:30:00Z', **kwargs}


class FakeGitHub:
    def __init__(self):
        self.repository = REPO
        self.metadata = {'full_name': REPO, 'private': False, 'default_branch': 'main'}
        self.existing, self.sha = '', None
        self.items = [release()]
        self.writes = []
        self.reads = 0
        self.failures = []
        self.on_conflict = lambda: None

    def document(self, branch):
        self.reads += 1
        return self.existing, self.sha

    def releases(self):
        return self.items

    def api(self, path='', method='GET', data=None):
        if path == '' and method == 'GET':
            return self.metadata
        assert path == '/contents/CHANGELOG.md' and method == 'PUT'
        self.writes.append(data)
        if self.failures:
            self.on_conflict()
            raise changelog.ApiError(self.failures.pop(0))
        self.existing = base64.b64decode(data['content']).decode('utf-8')
        self.sha = 'new-sha'
        return {}


class ChangelogTests(unittest.TestCase):
    def sync(self, client):
        with redirect_stdout(StringIO()):
            return changelog.sync(client)

    def test_only_formal_versions_are_sorted_numerically_and_use_public_release_links(self):
        items = [release('v0.1.3'), release('v0.1.10'), release('v0.1.2'),
                 release('v9.0.0', draft=True), release('v8.0.0', prerelease=True),
                 release('v0.2.0-beta'), release('build-assets-v1')]
        text = changelog.render(REPO, items)
        self.assertLess(text.index('## [0.1.10]'), text.index('## [0.1.3]'))
        self.assertLess(text.index('## [0.1.3]'), text.index('## [0.1.2]'))
        self.assertNotIn('9.0.0', text)
        self.assertNotIn('8.0.0', text)
        self.assertNotIn('beta', text)
        self.assertNotIn('build-assets', text)
        self.assertIn('https://github.com/example/releases/releases/tag/v0.1.3', text)
        self.assertNotIn('/commit/', text)
        self.assertIn('2026-11-13 02:30（UTC+8）', text)
        self.assertIn('- 自动测速\n- 自动换源', text)

    def test_release_edits_replace_one_entry_and_preserve_text_outside_managed_block(self):
        old = '自定义前言\n' + changelog.render(REPO, [release(body='旧说明')]) + '\n自定义后记'
        updated = changelog.render(REPO, [release(body='修正后的说明')], old)
        self.assertEqual(updated.count('## [0.1.3]'), 1)
        self.assertNotIn('旧说明', updated)
        self.assertIn('修正后的说明', updated)
        self.assertTrue(updated.startswith('自定义前言\n'))
        self.assertTrue(updated.endswith('\n自定义后记'))
        self.assertEqual(changelog.render(REPO, [release(body='修正后的说明')], updated), updated)

    def test_missing_notes_and_no_releases_have_explicit_placeholders(self):
        self.assertIn('此版本未提供更新说明', changelog.render(REPO, [release(body=None)]))
        self.assertIn('暂无正式发布版本', changelog.render(REPO, []))

    def test_corrupt_markers_duplicates_naive_dates_and_oversized_content_are_rejected(self):
        for old in ['手工日志', changelog.START, changelog.END + changelog.START, changelog.START * 2 + changelog.END]:
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'markers'):
                changelog.render(REPO, [release()], old)
        with self.assertRaisesRegex(ValueError, 'reserved'):
            changelog.render(REPO, [release(body=changelog.END)])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            changelog.render(REPO, [release('v0.1.3'), release('0.1.3')])
        with self.assertRaisesRegex(ValueError, 'timezone'):
            changelog.render(REPO, [release(published_at='2026-11-12T18:30:00')])
        with patch.object(changelog, 'MAX_DOCUMENT', 20), self.assertRaisesRegex(ValueError, 'too large'):
            changelog.render(REPO, [release()])

    def test_first_sync_creates_file_and_repeated_sync_does_not_create_another_commit(self):
        client = FakeGitHub()
        self.assertTrue(self.sync(client))
        self.assertEqual(len(client.writes), 1)
        self.assertNotIn('sha', client.writes[0])
        self.assertFalse(self.sync(client))
        self.assertEqual(len(client.writes), 1)

    def test_concurrent_write_reloads_both_document_and_releases_before_retry(self):
        for status in [409, 422]:
            client = FakeGitHub()
            client.failures = [status]
            def concurrent_write():
                client.existing = '保留前言\n' + changelog.render(REPO, [release('v0.1.10')])
                client.sha = 'concurrent-sha'
                client.items = [release('v0.1.3'), release('v0.1.10')]
            client.on_conflict = concurrent_write
            self.assertTrue(self.sync(client))
            self.assertEqual(client.reads, 2)
            self.assertEqual(client.writes[-1]['sha'], 'concurrent-sha')
            self.assertIn('## [0.1.10]', client.existing)
            self.assertIn('## [0.1.3]', client.existing)
            self.assertTrue(client.existing.startswith('保留前言\n'))

    def test_repeated_conflicts_stop_after_three_attempts_and_permission_failure_is_not_retried(self):
        for status, expected_attempts in [(409, 3), (403, 1)]:
            client = FakeGitHub()
            client.failures = [status] * 4
            with self.assertRaises(changelog.ApiError):
                self.sync(client)
            self.assertEqual(len(client.writes), expected_attempts)
            self.assertEqual(client.existing, '')

    def test_private_or_wrong_destination_is_rejected_before_any_file_access(self):
        for field, value in [('private', True), ('full_name', 'other/repository')]:
            client = FakeGitHub()
            client.metadata[field] = value
            with self.assertRaisesRegex(ValueError, 'public release repository'):
                self.sync(client)
            self.assertEqual(client.reads, 0)
            self.assertEqual(client.writes, [])

    def test_pagination_reads_every_page_and_incomplete_listing_never_writes(self):
        client = changelog.GitHub(REPO, 'not-a-real-token')
        with patch.object(client, 'api', side_effect=[[release()] * 100, [release('v0.1.2')]]) as api:
            self.assertEqual(len(client.releases()), 101)
            self.assertTrue(api.call_args.args[0].endswith('page=2'))
        with patch.object(client, 'api', return_value=[release()] * 100) as api:
            with self.assertRaisesRegex(ValueError, 'pagination limit'):
                client.releases()
            self.assertEqual(api.call_count, 100)
        client = FakeGitHub()
        with patch.object(client, 'releases', side_effect=changelog.ApiError(502)):
            with self.assertRaises(changelog.ApiError):
                self.sync(client)
            self.assertEqual(client.writes, [])

    def test_document_only_treats_404_as_absent_and_does_not_follow_links(self):
        client = changelog.GitHub(REPO, 'not-a-real-token')
        with patch.object(client, 'api', side_effect=changelog.ApiError(404)):
            self.assertEqual(client.document('main'), ('', None))
        with patch.object(client, 'api', side_effect=changelog.ApiError(403)):
            with self.assertRaises(changelog.ApiError):
                client.document('main')
        with patch.object(client, 'api', return_value={'type': 'symlink', 'encoding': 'base64'}):
            with self.assertRaisesRegex(ValueError, 'ordinary'):
                client.document('main')

    def test_api_errors_do_not_log_response_body_or_credentials(self):
        client = changelog.GitHub(REPO, 'not-a-real-token')
        client.opener = Mock()
        client.opener.open.side_effect = HTTPError('https://api.github.com', 403, 'Denied', None, BytesIO(b'sensitive-response'))
        with self.assertRaises(changelog.ApiError) as error:
            client.api()
        self.assertNotIn('sensitive-response', str(error.exception))
        self.assertNotIn(client.token, str(error.exception))
        self.assertIsNone(changelog.NoRedirect().redirect_request(None, None, None, None, None, None))


if __name__ == '__main__':
    unittest.main()
