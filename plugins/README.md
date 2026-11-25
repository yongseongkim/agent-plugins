# 플러그인 사용법

## 한 번만 참조할 때

플러그인 폴더에서 `skills/<스킬 이름>/SKILL.md`의 링크나 경로를 에이전트에 건네고 작업을 요청합니다.
[영상 분석](video-analysis/README.md)에서 스크립트를 실행하려면 해당 스킬 폴더도 함께 받아야 합니다.

## 플러그인으로 설치할 때

아래는 주석 교정 플러그인을 선택하는 예입니다.
영상 분석을 쓰려면 설치 명령의 `korean-dev-prose`를 `video-analysis`로 바꿉니다.

### Codex

```sh
codex plugin marketplace add yongseongkim/agent-plugins
codex plugin add korean-dev-prose@yongseong-plugins
```

### Claude Code

```sh
claude plugin marketplace add yongseongkim/agent-plugins
claude plugin install korean-dev-prose@yongseong-plugins
```

### Antigravity CLI

```sh
git clone https://github.com/yongseongkim/agent-plugins.git
cd agent-plugins
agy plugin install ./plugins/korean-dev-prose
```

## 영상 분석 스킬만 설치할 때

저장소 루트에서 Python 3.9 이상으로 실행합니다.
여러 프로젝트에서 사용하려면 사용자 설치를, 팀과 버전을 공유하려면 프로젝트 설치를 선택합니다.

```sh
python3 install.py --user
```

```sh
python3 install.py --project /path/to/project
```

기본 설치 대상은 세 도구이며, 하나만 고르려면 `--agent codex`, `--agent claude`, `--agent antigravity` 중 하나를 붙입니다.

| 도구 | 사용자 설치 경로 | 프로젝트 안의 설치 경로 |
| --- | --- | --- |
| [Codex](https://developers.openai.com/codex/skills/) | `~/.agents/skills/video-analysis/` | `.agents/skills/video-analysis/` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/video-analysis/` | `.claude/skills/video-analysis/` |
| [Antigravity](https://antigravity.google/docs/skills) | `~/.gemini/config/skills/video-analysis/` | `.agents/skills/video-analysis/` |

설치 프로그램은 스킬을 복사하며, 설치된 내용이 다르면 해당 경로를 출력하고 멈춥니다.
새 세션에서 Codex는 `$video-analysis`, Claude Code와 Antigravity는 `/video-analysis`에 영상 링크나 파일 경로와 질문을 전달합니다.
준비할 도구와 입력 형식은 [자료 수집 안내](video-analysis/skills/video-analysis/references/collection.md)에 있습니다.

## 플러그인을 추가할 때

아래 경로와 명령은 저장소 루트 기준입니다.

1. `plugins/<플러그인 이름>/plugin.json`과 해당 폴더의 `.claude-plugin/plugin.json`에 같은 이름, 버전, 용도를 적습니다.
2. 그 폴더의 `skills/<스킬 이름>/SKILL.md`에 지침을 씁니다.
   함께 배포할 스크립트와 참고 자료는 해당 스킬 폴더에 둡니다.
3. [Codex 목록](../.agents/plugins/marketplace.json)과 [Claude Code 목록](../.claude-plugin/marketplace.json)에 플러그인을 등록합니다.
4. `agy plugin validate --strict ./plugins/<플러그인 이름>`과 `claude plugin validate .claude-plugin/marketplace.json`으로 구성을 확인합니다.
5. `python3 -m unittest discover -s tests -v`로 설치와 영상 분석을 검증합니다. FFmpeg가 있으면 원본 프레임의 시각도 검사합니다.
