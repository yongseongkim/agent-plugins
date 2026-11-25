# video-analysis

YouTube 또는 로컬 영상에서 무슨 일이 언제 일어났는지 확인하는 에이전트 스킬입니다. 자막·음성 전사·화면 OCR을 같은 시간축에 모으고, 텍스트만으로 판단하기 어려운 구간은 원본 프레임을 직접 열어 봅니다. 같은 근거로 영상 요약, 장소 확인, 차트 분석처럼 서로 다른 질문에 답할 수 있습니다.

## 영상 분석 스킬을 직접 설치할 때

세 도구에서 플러그인으로 설치하는 방법은 [저장소 안내](../../README.md)에 있습니다.
아래 절차는 저장소 루트의 `install.py`로 영상 분석 스킬만 복사하는 방법입니다.

Python 3.9 이상으로 실행합니다. 기본값은 Codex, Claude Code, Google Antigravity 세 곳입니다. 필요한 도구만 고르려면 `--agent codex`, `--agent claude`, `--agent antigravity`를 지정합니다.

```sh
git clone https://github.com/yongseongkim/agent-plugins.git
cd agent-plugins
```

사용자 설치는 여러 프로젝트에서 쓸 때 선택합니다.

```sh
python3 install.py --user
```

프로젝트 설치는 팀과 함께 관리할 때 선택합니다. 설치된 스킬 디렉터리를 대상 저장소에 커밋하면 팀원이 같은 버전을 사용합니다.

```sh
python3 install.py --project /path/to/project
```

| 클라이언트 | 사용자 설치 경로 | 프로젝트 루트 기준 설치 경로 |
|---|---|---|
| [Codex](https://developers.openai.com/codex/skills/) | `~/.agents/skills/video-analysis/` | `.agents/skills/video-analysis/` |
| [Claude Code](https://code.claude.com/docs/en/skills) | `~/.claude/skills/video-analysis/` | `.claude/skills/video-analysis/` |
| [Google Antigravity](https://antigravity.google/docs/skills) | `~/.gemini/config/skills/video-analysis/` | `.agents/skills/video-analysis/` |

설치 프로그램은 [스킬 폴더](skills/video-analysis/)를 복사하므로 설치 후 원본 체크아웃을 옮길 수 있습니다. 프로젝트의 Codex와 Antigravity는 복사본 하나를 공유합니다. 같은 버전으로 다시 실행해도 결과가 같습니다. 기존 설치본의 내용이 다를 때는 그 경로를 출력하고 멈춥니다. 업데이트 시에는 해당 경로와 새 스킬 폴더의 차이를 확인한 뒤 교체합니다.

## 사용

새 세션에서 Codex는 `$video-analysis`, Claude Code와 Antigravity는 `/video-analysis`로 호출합니다. 영상 URL이나 로컬 파일 경로와 함께 질문을 전달합니다.

> 이 영상의 내용을 구간별로 정리해 줘. 4분쯤 발표자가 설정을 바꾸는 장면은 전후 화면을 비교하고, 실제로 확인한 값과 시각을 알려 줘.

에이전트는 `evidence_timeline.json`에서 발화와 화면 글자의 시간·출처를 확인하고, 필요한 시각에 JPEG를 추출해 살펴봅니다. 직접 확인한 프레임의 재생 시각은 `frames.json`에 저장됩니다. 다른 작업에서 재사용할 때는 목적별 `analysis.json`으로 근거, 결론, 미확인 사항을 전달합니다. [스킬 지침](skills/video-analysis/SKILL.md)

## 실행 환경

| 작업 | 사용하는 도구 |
|---|---|
| 기존 증거 타임라인 구성 | Python 표준 라이브러리 |
| YouTube 영상·자막 수집 | yt-dlp, FFmpeg |
| 특정 시각의 원본 프레임 확인 | FFmpeg, 이미지 입력을 지원하는 에이전트 |
| 로컬 음성 전사 | Apple Silicon용 MLX Whisper 또는 기존 Whisper 구간 JSON |
| 화면 글자 추출 | macOS Vision·Swift 또는 기존 OCR JSON/JSONL |

설치 프로그램은 스킬 파일만 복사합니다. 영상 수집이나 분석에 필요한 도구와 원본·자막의 준비 방법은 [자료 수집 안내](skills/video-analysis/references/collection.md)에 있습니다.

## 테스트

```sh
python3 -m unittest discover -s tests -v
```

FFmpeg가 있으면 실제 시험 영상을 생성하여 프레임 시각도 검사합니다.
