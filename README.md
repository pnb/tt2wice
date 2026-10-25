# Two-language Audio Books via TTS

This project creates two-language audio books from text using automatic translation and text-to-speech (TTS). The point is to create audio books that say each sentence in the original language, followed by the target language, to help with listening skills for language learners. In practice, some sentences are too long or too short, so it is not quite at the sentence level, but that's the idea.

## Installation

### Translation LLM

It is all intended to work with [llama.cpp](https://github.com/ggml-org/llama.cpp). The translation model can actually be any OpenAI endpoint, specified with an optional CLI argument, but the default assumption is a local llama.cpp server running at `http://localhost:8090/v1`.

Example:

```bash
./llama-server -m google_gemma-4-E4B-it-Q5_K_M.gguf --load-mode none -c 16000 --port 8090 --reasoning off
```

### TTS (Supertonic)

TTS is done with [Supertonic](https://github.com/supertone-oss-archive/supertonic), a fast, fully local, multilingual (31 languages) TTS system. It runs on CPU fast enough. On first run, the TTS model is downloaded automatically from HuggingFace into `~/.cache/supertonic3/`.

Voices are one of Supertonic's 10 built-in voices: M1-M5 (male) and F1-F5 (female), which you can specify by command-line arguments (see below).

### Python setup

Requires Python and the `supertonic`, `openai`, and `pandas` packages, and separately (non-Python) installation of FFmpeg (e.g., `dnf install ffmpeg`, `apt install ffmpeg`).

## Usage

See the command-line help:

```bash
python main.py -h
```

Example:

```bash
python main.py pg36.txt out/ --voice1 M5 --voice2 F3 --trans-lang nl --pg
```

`--voice1` is the voice for the original text, `--voice2` for the translation, and `--trans-lang` is the ISO code of the translation language (e.g., `nl`, `es`). The language of the input text is detected automatically.

## TODO

Roughly in order of priority:

- [x] Un-hardcode the LLM API URL and key
- [x] Add support for specifying languages instead of hardcoded English/Dutch
- [x] Track length of individual output chunks to check problems, e.g., when TTS produces a short output like "Nngggg" or "CSCHHHHHH" when it is supposed to actually say something
- [x] Figure out what the actual required packages are (I think there were more)
- [ ] Add title/author metadata to audio files
- [ ] Add chapter break metadata to output
- [ ] Translation could probably be improved with a better prompt that incorporates the context of the sentence/fragment
- [ ] Add support for other text sources than Project Gutenberg (and auto-detect the format)
