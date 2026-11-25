# 개인 에이전트 플러그인

개인 워크플로를 플러그인으로 배포한다.
설치와 등록 절차는 [플러그인 사용법](plugins/README.md)에 있다.

| 작업 | 처음 볼 곳 |
| --- | --- |
| 주석과 개발 문서의 교정 기준 변경 | [edit-korean-dev-prose/SKILL.md](plugins/korean-dev-prose/skills/edit-korean-dev-prose/SKILL.md) |
| 영상 분석에서 자막·전사·OCR을 시간순으로 합치는 방식 변경 | [video_evidence.py](plugins/video-analysis/skills/video-analysis/scripts/video_evidence.py)의 `build_timeline`과 [테스트](tests/test_video_analysis.py) |
| 플러그인 추가 또는 목록에서 누락된 항목 확인 | [Codex 목록](.agents/plugins/marketplace.json), [Claude Code 목록](.claude-plugin/marketplace.json), [두 목록과 패키지를 대조하는 테스트](tests/test_catalog.py) |
| 영상 분석 스킬의 단독 설치 경로 변경 | [install.py](install.py)와 [설치 테스트](tests/test_install.py) |
