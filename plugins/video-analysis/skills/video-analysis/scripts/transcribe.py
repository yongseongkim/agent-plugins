"""Transcribe one complete media file with MLX Whisper on Apple Silicon."""

import argparse
from importlib.metadata import version
from pathlib import Path

import mlx_whisper
from video_evidence import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--language", default="auto", help="Spoken language code or auto")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-mlx")
    args = parser.parse_args()
    result = mlx_whisper.transcribe(
        str(args.media), path_or_hf_repo=args.model, language=None if args.language == "auto" else args.language,
        task="transcribe", word_timestamps=True, condition_on_previous_text=False,
        verbose=None,
    )
    if not isinstance(result.get("segments"), list):
        raise ValueError("Expected a list of speech segments")
    result.update(model=args.model, engine="mlx-whisper", engine_version=version("mlx-whisper"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(f"{args.media.name}: {len(result['segments'])} segments", flush=True)


if __name__ == "__main__":
    main()
