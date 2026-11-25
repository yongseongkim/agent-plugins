# 개인 에이전트 플러그인

에이전트와 작업할 때 쓰는 [개인 워크플로](plugins/)를 모았습니다.

## 설치

한국어 주석과 문서를 교정하는 플러그인을 설치하려면, 사용하는 도구에 맞춰 터미널에서 아래 명령을 실행합니다.

### Codex CLI

```sh
codex plugin marketplace add yongseongkim/agent-plugins
codex plugin add korean-dev-prose@yongseong-plugins
```

설치한 뒤 새 Codex 세션에서 `$`를 입력해 `edit-korean-dev-prose`를 선택하고 “이번 PR의 주석을 다듬어줘”라고 요청합니다.

### Claude Code

```sh
claude plugin marketplace add yongseongkim/agent-plugins
claude plugin install korean-dev-prose@yongseong-plugins
```

새 Claude Code 세션에 `/korean-dev-prose:edit-korean-dev-prose 이번 PR의 주석을 다듬어줘`를 입력합니다.

### Antigravity CLI (agy)

```sh
git clone https://github.com/yongseongkim/agent-plugins.git
cd agent-plugins
agy plugin install ./plugins/korean-dev-prose
```

이미 저장소를 내려받았다면 저장소 루트에서 마지막 줄만 실행합니다.
교정할 프로젝트에서 새 `agy` 세션을 열고 `/edit-korean-dev-prose 이번 PR의 주석을 다듬어줘`를 입력합니다.
