"""仅根据公开正式 Release 生成版本历史，不读取应用源码或 Git 提交。"""
import base64
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

START = '<!-- cmobstool-changelog:start -->'
END = '<!-- cmobstool-changelog:end -->'
HEADER = '# 更新日志\n\n这里归档 CMObsTool 正式发布版本的更新说明，最新版本在前。\n\n此文件根据 GitHub Releases 自动同步。修改版本说明请编辑对应 Release。\n\n'
VERSION = re.compile(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)\Z')
MAX_DOCUMENT = 900 * 1024


class ApiError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f'GitHub API request failed (HTTP {status})')


class NoRedirect(HTTPRedirectHandler):
    # API 只访问固定域名；禁止重定向转发工作流凭据。
    def redirect_request(self, *args, **kwargs):
        return None


class GitHub:
    def __init__(self, repository, token):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository name')
        self.repository, self.token = repository, token
        self.opener = build_opener(NoRedirect())

    def api(self, path='', method='GET', data=None):
        headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'CMObsTool-changelog', 'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        body = json.dumps(data).encode('utf-8') if data is not None else None
        if body is not None:
            headers['Content-Type'] = 'application/json'
        request = Request(f'https://api.github.com/repos/{self.repository}{path}', data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                payload = response.read(16 * 1024 * 1024 + 1)
        except HTTPError as error:
            # 不把服务端原始响应或请求头输出到 Actions 日志。
            raise ApiError(error.code) from None
        if len(payload) > 16 * 1024 * 1024:
            raise ValueError('GitHub response is too large; no changelog was written')
        return json.loads(payload)

    def releases(self):
        result = []
        for page in range(1, 101):
            batch = self.api(f'/releases?per_page=100&page={page}')
            if not isinstance(batch, list):
                raise ValueError('Invalid release listing')
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise ValueError('Release pagination limit reached; refusing to publish incomplete history')

    def document(self, branch):
        try:
            entry = self.api('/contents/CHANGELOG.md?ref=' + quote(branch, safe=''))
        except ApiError as error:
            if error.status == 404:
                return '', None
            raise
        if entry.get('type') != 'file' or entry.get('encoding') != 'base64':
            raise ValueError('CHANGELOG.md must be an ordinary UTF-8 file')
        content = base64.b64decode(entry['content']).decode('utf-8')
        return content, entry['sha']


def render(repository, releases, existing=''):
    entries = []
    versions = set()
    for release in releases:
        tag = release.get('tag_name', '')
        match = VERSION.fullmatch(tag)
        if release.get('draft') or release.get('prerelease') or not match:
            continue
        version = tuple(map(int, match.groups()))
        if version in versions:
            raise ValueError('Duplicate stable release version')
        versions.add(version)
        published = datetime.fromisoformat(release['published_at'].replace('Z', '+00:00'))
        if published.tzinfo is None:
            raise ValueError('Release date must include a timezone')
        date = published.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
        notes = (release.get('body') or '').replace('\r\n', '\n').strip() or '此版本未提供更新说明。'
        if START in notes or END in notes:
            raise ValueError('Release notes contain reserved changelog markers')
        url = f'https://github.com/{repository}/releases/tag/{quote(tag, safe="")}'
        entries.append((version, f'## [{".".join(map(str, version))}]({url})\n\n发布日期：{date}（UTC+8）\n\n{notes}'))
    entries.sort(key=lambda entry: entry[0], reverse=True)
    history = '\n\n---\n\n'.join(content for _, content in entries) or '暂无正式发布版本。'
    managed = f'{START}\n\n{history}\n\n{END}'
    if not existing:
        result = HEADER + managed + '\n'
    else:
        # 只替换自动管理区，保留用户在其前后补充的文字；缺失/损坏标记时拒绝覆盖。
        if existing.count(START) != 1 or existing.count(END) != 1 or existing.index(START) > existing.index(END):
            raise ValueError('Changelog markers are missing or damaged; no existing content was overwritten')
        start, end = existing.index(START), existing.index(END) + len(END)
        result = existing[:start] + managed + existing[end:]
    if len(result.encode('utf-8')) > MAX_DOCUMENT:
        raise ValueError('Changelog is too large; split history before retrying')
    return result


def sync(client):
    repository = client.api()
    if repository.get('private') is not False or repository.get('full_name', '').lower() != client.repository.lower():
        raise ValueError('Changelog destination must be the intended public release repository')
    branch = repository['default_branch']
    for attempt in range(3):
        # 先读文件 SHA 再拉 Release，旧快照不能覆盖并发写入的新历史；冲突后全部重读。
        existing, sha = client.document(branch)
        content = render(client.repository, client.releases(), existing)
        if content == existing:
            print('CHANGELOG.md is already up to date.')
            return False
        data = {'message': 'docs: 同步正式版本更新日志', 'content': base64.b64encode(content.encode('utf-8')).decode('ascii'), 'branch': branch}
        if sha is not None:
            data['sha'] = sha
        try:
            client.api('/contents/CHANGELOG.md', method='PUT', data=data)
        except ApiError as error:
            if error.status in (409, 422) and attempt < 2:
                continue
            raise
        print(f'Updated https://github.com/{client.repository}/blob/{quote(branch, safe="")}/CHANGELOG.md')
        return True
    raise RuntimeError('Unable to update changelog')


def main():
    token = os.environ.get('GH_TOKEN')
    if not token:
        raise ValueError('GH_TOKEN is required; use the workflow repository token')
    sync(GitHub(os.environ.get('GITHUB_REPOSITORY', ''), token))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print(f'Changelog sync failed: {error}', file=sys.stderr)
        sys.exit(1)
