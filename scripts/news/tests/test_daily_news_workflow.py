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
        env={**os.environ, 'PATH': str(tmp_path), 'COMMAND_LOG': str(commands), 'SCENARIO': scenario},
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
