# Collect video evidence

Use the caller's media and retention settings. `RUN` is the directory for one video, `SKILL` is the skill directory, and `VIDEO` is the original media path. Start with the inputs already available.

## Media, captions, and metadata

List captions and replace `ko` with the source language. Record whether the track is uploader-provided or auto-generated. To keep both for one language, download them separately to different paths.

```sh
yt-dlp --no-playlist --list-subs -- "$URL"
yt-dlp --no-playlist --write-info-json --write-subs --write-auto-subs \
  --sub-langs ko --sub-format vtt --convert-subs vtt \
  -o "$RUN/source/%(id)s.%(ext)s" --print after_move:filepath -- "$URL"
```

Use the printed path for `VIDEO`. Copy or link the original `.info.json` to `$RUN/metadata.json` and the selected track to `$RUN/captions.vtt`. Read the description and chapters from metadata. For local files, assign a stable video ID. Record access failures. Use external transcription only when selected by the caller.

## Speech and on-screen text

On Apple Silicon, use local MLX Whisper for word timestamps. Set the language to match the speech.

```sh
uv run --with mlx-whisper python "$SKILL/scripts/transcribe.py" "$VIDEO" "$RUN/asr.json" --language ko
```

Other Whisper implementations can supply `asr.json` with `start`, `end`, and `text` on each segment. Check for audio with `ffprobe -v error -select_streams a -show_entries stream=index "$VIDEO"`. Record missing audio or unavailable tools. Attribute captions from silent media to the caption track.

For macOS Vision OCR, sample the original from time zero into a fresh empty frame directory. Match the sampling rate in both commands so file numbers map to playback time. Choose recognition languages for the on-screen writing.

```sh
mkdir -p "$RUN/ocr-frames"
ffmpeg -nostdin -n -i "$VIDEO" -vf fps=1:start_time=0:round=up -q:v 3 "$RUN/ocr-frames/%07d.jpg"
swift "$SKILL/scripts/ocr.swift" "$RUN/ocr-frames" 1 "$RUN/ocr.jsonl" ko-KR,en-US
```

For clips or irregular samples use the original frame times from `inspect_frames.py`. If Vision fails, record the failure and inspect the relevant frames directly. A successful scan may also return no text.

Other OCR tools can supply JSONL such as `{"time":12.0,"lines":[{"text":"OPEN","confidence":0.92}]}`. Each Vision line also has `x`, `y`, `width`, and `height`, normalized to 0–1 from the top left of the original frame. Timeline OCR events expose these as `boundingBox`. Segment JSON accepts the same box at `segments[].boundingBox`. Text and timing remain usable with missing or invalid coordinates. Check regions separately when signs and captions use different languages. Attribute on-screen writing to OCR.

## Existing inputs

The timeline builder selects the first available file in each row and preserves the originals.

| Track | Input files in order |
|---|---|
| Captions or reviewed primary transcript | `transcripts.reviewed.json`, `transcripts.json`, `captions.json`, `captions.vtt` |
| Speech | `audio_transcript.json`, `asr.json` |
| OCR | `onscreen_text.json`, `ocr.jsonl` |

Segment JSON uses `segments[]` with `start`, `end` or `duration`, and `text`. A sampled OCR frame needs only a start time. For `videos[]`, select the matching video ID. Preserve collection errors such as `{"videoId":"…","error":"…"}`. Combine evidence only on the same source timeline and count duplicated tracks once.
