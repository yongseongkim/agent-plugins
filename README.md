# 개인 에이전트 플러그인

에이전트와 작업할 때 쓰는 [개인 워크플로](plugins/)를 모았습니다.

## 설치

한국어 주석과 문서를 교정하려면 사용하는 도구의 설치 명령을 실행합니다.

```sh
# Codex CLI
codex plugin marketplace add yongseongkim/agent-plugins
codex plugin add korean-dev-prose@yongseong-plugins
```

```sh
# Claude Code
claude plugin marketplace add yongseongkim/agent-plugins
claude plugin install korean-dev-prose@yongseong-plugins
```

```sh
# Antigravity CLI (agy). 이미 내려받았다면 저장소 루트에서 마지막 줄만 실행합니다.
git clone https://github.com/yongseongkim/agent-plugins.git
cd agent-plugins
agy plugin install ./plugins/korean-dev-prose
```

설치한 뒤 작업할 프로젝트에서 새 세션을 열고 “edit-korean-dev-prose로 이번 PR의 주석을 다듬어줘”라고 요청합니다.
