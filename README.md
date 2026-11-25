# 개인 에이전트 플러그인

에이전트와 작업할 때 쓰는 [개인 워크플로](plugins/)를 모았습니다.

## 설치

Codex CLI에서 한국어 주석과 문서를 교정하는 플러그인을 쓰려면 터미널에서 다음 두 줄을 실행합니다.

```sh
codex plugin marketplace add yongseongkim/agent-plugins
codex plugin add korean-dev-prose@yongseong-plugins
```

설치한 뒤 새 Codex 세션에서 `$`를 입력해 `edit-korean-dev-prose`를 선택하고 “이번 PR의 주석을 다듬어줘”라고 요청합니다.

다른 도구의 설치 방법은 [Claude Code](plugins/README.md#claude-code)와 [Antigravity CLI](plugins/README.md#antigravity-cli) 안내에 있습니다.
