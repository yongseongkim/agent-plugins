---
name: video-analysis
description: Analyze YouTube or local videos with captions, speech, and frames. Use for summaries, scene questions, or timestamped evidence that another task can reuse.
---

# Video analysis

Use the user's question to set the scope. Cover the whole video for a summary, or the relevant scene and its context for a specific question. Follow the caller's output format and retention policy. Answer in the user's language and preserve source wording.

## Build the timeline

Reuse media, metadata, tracks, and reviews for the same video ID and version. Attempt captions, Whisper, and OCR independently and keep the originals. For missing inputs, see [collection](references/collection.md). Reuse `evidence_timeline.json` when its input fingerprint is current. To rebuild it, set `SKILL` to this skill's absolute path and `RUN` to the video's working directory.

```sh
python3 "$SKILL/scripts/video_evidence.py" "$RUN" --video-id "$VIDEO_ID"
```

Read each event's source, text, and playback time. Check `sources` for missing, empty, failed, or duplicate tracks.
`durationSeconds` is the latest end time among the text events, or zero when there are none.
Compare it with the media duration and inspect gaps when the answer depends on silent action.

## Interpret scenes

Use the title, description, and chapters for context. Split on changes in topic or action. For each section, identify what happened, cite the evidence, and note what still needs a visual check.

- Check unfamiliar names in Whisper against nearby speech, captions, and on-screen text. When a creator's reply names something in a timestamped viewer question, cite both texts and links. Use `null` for an unknown scene time, including description-only mentions. Comment posting dates are separate from playback time. Reserve zero for evidence at the start.
- Compare OCR `boundingBox` values across frames. Changing text in a stable area that follows speech suggests embedded captions. Reassess when the layout changes. Captions repeating speech can confirm the wording but count as one claim.
- Match the evidence to the claim. A shop sign establishes visibility. A visit or recommendation needs supporting action, speech, or creator commentary.

## Inspect frames when the answer depends on the image

If the tracks answer the question, cite them. For ambiguous text, conflicting numbers, or unspoken action, name the question and choose the relevant times. Use chapters or spaced samples when the time is unknown. Reuse full frames when available. To extract more, pass their playback times to the helper.

```sh
python3 "$SKILL/scripts/inspect_frames.py" "$VIDEO" --at 378 380 382 \
  --question 'Which value changes, and when?' --out "$RUN/visual"
```

Open the images with an image viewer. Compare adjacent frames for motion, sample closer around fast changes, and zoom at source resolution for small labels. Even a static shot can contain a UI change. Cite the actual frame time from `frames.json` and preserve signs, decimals, and units. Distinguish what you saw from what you inferred. Mark anything unreadable or unavailable as unverified.

## Return evidence

For a direct question, give the answer. When the evidence comes from a scene, cite its playback time and link to it when available.
For reuse, write `analysis.json` in a purpose-specific directory. Each analysis references the shared timeline.

- Include `videoId`, `purpose`, `timelineFingerprint` (the timeline's `inputFingerprint`), and `coverage` (scope, track status, gaps).
- Each entry in `sections[]` carries `startSeconds`, `endSeconds`, `summary`, and `evidence`. Cite a file and event index, a comment link, or an actual frame time.
- In `visualChecks[]`, record the question, source time, observations, and unresolved details. Keep the original video link and time if the caller discards local media.
- Use `findings[]` for conclusions and their evidence. Identify the action or statement supporting each inference. Leave downstream review and storage to the caller.
