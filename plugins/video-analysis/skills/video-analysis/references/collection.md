# 자료 수집

원본과 증거 파일의 위치는 호출한 작업이 정한다. 아래 예에서는 한 영상만 담긴 작업 폴더를 `RUN`, 스킬 폴더를 `SKILL`, 실제 영상 경로를 `VIDEO`로 둔다. 기존 자료가 있으면 해당 단계에서 바로 시작한다.

## 원본, 자막, 메타데이터

YouTube URL이면 사용 가능한 원어 자막부터 확인한다. 아래 예시의 `ko`를 실제 자막 언어로 바꾼다. 업로더 자막과 자동 생성 자막의 출처를 기록하고 둘 다 보존해야 하는 작업은 각각 별도 출력 경로로 받는다.

```sh
yt-dlp --no-playlist --list-subs -- "$URL"
yt-dlp --no-playlist --write-info-json --write-subs --write-auto-subs \
  --sub-langs ko --sub-format vtt --convert-subs vtt \
  -o "$RUN/source/%(id)s.%(ext)s" --print after_move:filepath -- "$URL"
```

출력된 원본 경로를 `VIDEO`로 사용한다. 원본 `.info.json`을 `RUN/metadata.json`에, 사용할 트랙을 `RUN/captions.vtt`에 복사하거나 연결한다. 설명란과 챕터는 메타데이터에서 읽는다. 로컬 영상은 원본 파일을 사용하며 안정적인 ID를 지정한다. 접근 제한이나 실패 원인을 기록한다. 외부 전사 서비스는 따로 선택한 경우에만 사용한다.

## 로컬 음성 전사와 OCR

Apple Silicon에서 단어 시각이 필요한 경우 기존 MLX Whisper 환경을 사용한다. `--language ko`는 발화 언어에 맞춘다.

```sh
uv run --with mlx-whisper python "$SKILL/scripts/transcribe.py" "$VIDEO" "$RUN/asr.json" --language ko
```

오디오 스트림 여부는 `ffprobe -v error -select_streams a -show_entries stream=index "$VIDEO"`로 확인할 수 있다. 음성 트랙이 없는 영상의 자막은 자막 근거로만 인용한다.

다른 환경에서도 로컬 Whisper의 `segments[].start/end/text` JSON을 `asr.json`으로 사용할 수 있다. 음성이 없거나 도구를 실행할 수 없으면 그 상태를 결과에 기록한다.

macOS의 전체 화면 OCR 예시는 다음과 같다. 영상 시작부터 새로운 빈 프레임 폴더에 같은 간격으로 뽑아야 파일 번호와 표본 시각이 맞는다. 아래 OCR은 정규 간격 표본 전용이다. 잘라낸 영상이나 임의의 시각을 골라 추출한 프레임에는 `inspect_frames.py`의 원본 시각을 사용한다.

```sh
mkdir -p "$RUN/ocr-frames"
ffmpeg -nostdin -n -i "$VIDEO" -vf fps=1:start_time=0:round=up -q:v 3 "$RUN/ocr-frames/%07d.jpg"
swift "$SKILL/scripts/ocr.swift" "$RUN/ocr-frames" 1 "$RUN/ocr.jsonl" ko-KR,en-US
```

Vision이 실행 오류로 종료되면 글자가 없다는 뜻으로 해석하지 않는다. 실패 상태를 기록하고, 필요한 구간은 원본 프레임을 직접 열어 확인한다.

다른 환경에서는 기존 OCR로 `{"time":12.0,"lines":[{"text":"표시값","confidence":0.92}]}` 형식의 JSONL 또는 아래 구간 JSON을 쓴다. 촬영지 언어와 화면 자막 언어가 다르면 필요한 영역과 언어를 따로 확인한다. 화면 글자를 발화로 옮기지 않는다.

Vision JSONL은 각 줄에 `x`, `y`, `width`, `height`를 기록한다. 원점은 원본 화면의 왼쪽 위이고 좌표와 크기는 0~1 비율이다.
타임라인의 OCR 이벤트는 이 값을 `boundingBox`에 담는다. 다른 OCR의 구간 JSON도 같은 좌표계로 변환한 값을 `segments[].boundingBox`로 넘길 수 있다. 좌표가 없거나 유효하지 않은 줄은 글자와 시각만으로도 분석할 수 있다.

## 기존 수집 자료

타임라인 도구는 영상별 디렉터리에서 다음 순서로 입력을 선택한다. 원본은 수정하지 않는다.

| 트랙 | 인식하는 파일 |
|---|---|
| 자막 또는 검토된 기본 전사 | `transcripts.reviewed.json`, `transcripts.json`, `captions.json`, `captions.vtt` |
| 음성 전사 | `audio_transcript.json`, `asr.json` |
| 화면 글자 | `onscreen_text.json`, `ocr.jsonl` |

구간 JSON은 `segments[]`에 `start`, `end` 또는 `duration`, `text`를 담는다. 분리된 프레임 한 장의 OCR은 시작 시각만 있어도 된다. `videos[]`에 여러 결과가 있으면 해당 영상 ID의 자료만 쓴다. `{"videoId":"…","error":"…"}` 형태의 수집 실패도 보존한다. 원본과 시각이 같은 자료만 합치고 동일 구간이 복제된 트랙은 독립적인 증거 수에서 제외한다.
