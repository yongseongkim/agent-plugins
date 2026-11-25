# 개인 에이전트 플러그인

Codex, Claude Code, Antigravity CLI에서 한국어 주석과 개발 문서를 다듬고 영상을 분석할 때 쓰는 플러그인 모음입니다.

## 시스템 구성

```text
agent-plugins/
|-- plugins/
|   |-- korean-dev-prose/   한국어 주석과 개발 문서의 교정 지침
|   `-- video-analysis/     영상 분석 지침과 전사·OCR·프레임 추출 스크립트
|-- .agents/plugins/        Codex 플러그인 목록
`-- .claude-plugin/         Claude Code 플러그인 목록
```

두 목록은 `plugins/` 아래의 같은 폴더를 가리킵니다.
Antigravity CLI에서는 사용할 플러그인 폴더를 직접 지정합니다.

| 플러그인 | 언제 쓰나요? | 스킬 |
| --- | --- | --- |
| `korean-dev-prose` | 한국어 주석과 개발 문서를 다듬으면서 코드에 드러나지 않는 이유를 보존할 때 | [edit-korean-dev-prose](plugins/korean-dev-prose/skills/edit-korean-dev-prose/SKILL.md) |
| `video-analysis` | YouTube나 로컬 영상에서 어떤 일이 언제 일어났는지 자막·음성·화면으로 확인할 때 | [video-analysis](plugins/video-analysis/skills/video-analysis/SKILL.md) · [실행 환경](plugins/video-analysis/README.md#실행-환경) |

## 한 번만 참조할 때

예를 들어 주석 한 줄을 고치려면 에이전트에 위 표의 교정 스킬 링크와 원문을 건네고 “이 지침에 맞게 주석을 다듬어줘”라고 요청합니다.
체크아웃한 저장소에서는 파일 경로를 건네도 됩니다.
영상 분석에서 스크립트를 실행하려면 해당 스킬 폴더도 함께 받아야 합니다.

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

## 플러그인을 추가할 때

1. `plugins/<플러그인 이름>/plugin.json`과 해당 폴더의 `.claude-plugin/plugin.json`에 같은 이름, 버전, 용도를 적습니다.
2. 그 폴더의 `skills/<스킬 이름>/SKILL.md`에 지침을 씁니다.
   함께 배포할 스크립트와 참고 자료는 해당 스킬 폴더에 둡니다.
3. [Codex 목록](.agents/plugins/marketplace.json)과 [Claude Code 목록](.claude-plugin/marketplace.json)에 플러그인을 등록하고 위 표에 스킬 링크를 추가합니다.
4. `agy plugin validate --strict ./plugins/<플러그인 이름>`과 `claude plugin validate .claude-plugin/marketplace.json`으로 구성을 확인합니다.
