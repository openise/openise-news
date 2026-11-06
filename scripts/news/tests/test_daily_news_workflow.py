"""Daily News の PR 工程を、git・gh の実行をモックして検証する。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

WORKFLOW = Path(__file__).resolve().parents[3] / '.github/workflows/daily-news.yml'


@pytest.mark.parametrize('scenario', [
    'new', 'existing', 'lookup_failure', 'create_failure', 'push_failure', 'merge_failure', 'no_changes',
])
def test_news_pr_step_reuses_open_pr_and_propagates_failures(tmp_path, scenario):
    # workflow 本体を実行し、テスト用に複製した処理とのずれを防ぐ。
    step = WORKFLOW.read_text().split('      - name: 差分があれば PR を作って merge する\n', 1)[1]
    script = textwrap.dedent(step.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0])
    commands = tmp_path / 'commands.jsonl'
    mock = tmp_path / 'mock'
    mock.write_text(f'#!{sys.executable}\n' + textwrap.dedent('''\
        import json
        import os
        from pathlib import Path
        import sys

        command = [Path(sys.argv[0]).name, *sys.argv[1:]]
        with open(os.environ['COMMAND_LOG'], 'a') as log:
            log.write(json.dumps(command) + '\\n')
        scenario = os.environ['SCENARIO']
        if command[0] == 'date':
            print('20261106')
        elif command[:2] == ['git', 'status'] and scenario != 'no_changes':
            print('?? src/content/news/20261106/')
        elif command[:2] == ['git', 'push'] and scenario == 'push_failure':
            sys.exit(1)
        elif command[:3] == ['gh', 'pr', 'list']:
            if scenario == 'lookup_failure':
                print('API request failed', file=sys.stderr)
                sys.exit(1)
            if scenario == 'existing':
                print('123')
        elif command[:3] == ['gh', 'pr', 'create'] and scenario == 'create_failure':
            sys.exit(1)
        elif command[:3] == ['gh', 'pr', 'merge'] and scenario == 'merge_failure':
            sys.exit(1)
        '''))
    mock.chmod(0o755)
    for name in ['git', 'gh', 'date']:
        (tmp_path / name).symlink_to(mock)
    result = subprocess.run(
        ['/bin/bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', script],
        cwd=tmp_path,
        env={**os.environ, 'PATH': str(tmp_path), 'COMMAND_LOG': str(commands),
             'SCENARIO': scenario, 'NEWS_DATE': '20261106'},
        text=True, capture_output=True,
    )
    calls = [json.loads(line) for line in commands.read_text().splitlines()]
    assert result.returncode == (1 if scenario.endswith('_failure') else 0)
    if scenario == 'no_changes':
        assert calls == [['git', 'status', '--porcelain', '--', 'src/content/news']]
        return
    push = ['git', 'push', '--force', 'origin', 'news/20261106']
    assert push in calls
    gh_calls = [call for call in calls if call[0] == 'gh']
    if scenario == 'push_failure':
        assert gh_calls == []
        return
    lookup = ['gh', 'pr', 'list', '--base', 'main', '--head', 'news/20261106',
              '--state', 'open', '--json', 'number', '--jq', '.[0].number // empty']
    create = ['gh', 'pr', 'create', '--base', 'main', '--head', 'news/20261106',
              '--title', 'chore: 20261106 の News を追加する',
              '--body', 'workflow（Daily News）が自動で作成した PR です。']
    merge = ['gh', 'pr', 'merge', 'news/20261106', '--squash', '--delete-branch']
    assert calls.index(push) < calls.index(lookup)
    if scenario == 'lookup_failure':
        assert gh_calls == [lookup]
        assert '::error::既存 PR の取得に失敗しました' in result.stdout
    elif scenario == 'existing':
        assert gh_calls == [lookup, merge]
        assert '既存 PR #123 を再利用します' in result.stdout
    elif scenario == 'create_failure':
        assert gh_calls == [lookup, create]
        assert '::error::PR の作成に失敗しました' in result.stdout
    else:
        assert gh_calls == [lookup, create, merge]


def test_workflow_keeps_target_date_across_jst_midnight(tmp_path):
    workflow = WORKFLOW.read_text()
    assert 'TZ: Asia/Tokyo' in workflow
    assert workflow.count('$(date ') == 1
    steps = workflow.split('      - name: ')
    assert steps[1].startswith('JST の対象日を固定する\n')
    commands = tmp_path / 'commands.jsonl'
    mock = tmp_path / 'mock'
    mock.write_text(f'#!{sys.executable}\n' + textwrap.dedent('''\
        import json
        import os
        from pathlib import Path
        import sys

        command = [Path(sys.argv[0]).name, *sys.argv[1:]]
        log = Path(os.environ['COMMAND_LOG'])
        previous = log.read_text() if log.exists() else ''
        with log.open('a') as stream:
            stream.write(json.dumps(command) + '\\n')
        if command[0] == 'date':
            # 開始は JST 23:59、収集開始後は翌日 00:01 とする。
            print('20261107' if 'python3' in previous else '20261106')
        elif command[0] == 'python3' and command[1].endswith('fetch_ai_news.py'):
            target = command[command.index('--date') + 1]
            path = Path('src/content/news') / target / 'index.md'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('## Hacker News（AI）\\n| 1 | 記事 | 10 |\\n')
        elif command[:2] == ['git', 'status']:
            print('?? src/content/news/20261106/')
        '''))
    mock.chmod(0o755)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for name in ['date', 'python3', 'git', 'gh']:
        (bin_dir / name).symlink_to(mock)
    for force in ['false', 'true']:
        commands.unlink(missing_ok=True)
        github_env = tmp_path / 'github_env'
        github_env.unlink(missing_ok=True)
        summary = tmp_path / 'summary'
        summary.unlink(missing_ok=True)
        env = {**os.environ, 'PATH': f'{bin_dir}:/usr/bin:/bin', 'COMMAND_LOG': str(commands),
               'GITHUB_ENV': str(github_env), 'GITHUB_STEP_SUMMARY': str(summary), 'FORCE': force}
        for step in steps[1:-1]:
            run = step.split('        run: ', 1)[1].split('\n      - ', 1)[0]
            script = textwrap.dedent(run[2:]) if run.startswith('|\n') else run.strip()
            result = subprocess.run(['/bin/bash', '-eo', 'pipefail', '-c', script],
                                    cwd=tmp_path, env=env, text=True, capture_output=True)
            assert result.returncode == 0, result.stderr
            env['NEWS_DATE'] = github_env.read_text().strip().split('=', 1)[1]
        calls = [json.loads(line) for line in commands.read_text().splitlines()]
        assert [call for call in calls if call[0] == 'date'] == [['date', '+%Y%m%d']]
        fetch = ['python3', 'scripts/news/fetch_ai_news.py', '--date', '20261106']
        assert fetch + (['--force'] if force == 'true' else []) in calls
        assert ['python3', 'scripts/news/curate_news.py', '--date', '20261106'] in calls
        assert ['git', 'switch', '-c', 'news/20261106'] in calls
        assert ['gh', 'pr', 'merge', 'news/20261106', '--squash', '--delete-branch'] in calls
        assert '2026-11-06' in summary.read_text()
        assert '| Hacker News | 1 |' in summary.read_text()
