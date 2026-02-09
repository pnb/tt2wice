# Two-language Audio Books via TTS

This project creates two-language audio books from text using automatic translation and text-to-speech (TTS). The point is to create audio books that say each sentence in the original language, followed by the target language, to help with listening skills for language learners. In practice, some sentences are too long or too short, so it is not quite at the sentence level, but that's the idea.

## Installation

Requires Python, `outetts` and `openai` packages, and separate installation of FFmpeg for final concatenation and conversion of output WAV files.

## Usage

See the command-line help:

```bash
python main.py -h
```

## TODO

Roughly in order of priority:

- [ ] Add support for specifying languages instead of hardcoded English/Dutch
- [ ] Track length of individual output chunks to check problems, e.g., when TTS produces a short output like "Nngggg" or "CSCHHHHHH" when it is supposed to actually say something
- [ ] Add title/author metadata to audio files
- [ ] Add chapter break metadata to output
- [ ] Translation could probably be improved with a better prompt that incorporates the context of the sentence/fragment
- [ ] Add support for other text sources than Project Gutenberg (and auto-detect the format)
