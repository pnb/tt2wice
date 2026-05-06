# Two-language Audio Books via TTS

This project creates two-language audio books from text using automatic translation and text-to-speech (TTS). The point is to create audio books that say each sentence in the original language, followed by the target language, to help with listening skills for language learners. In practice, some sentences are too long or too short, so it is not quite at the sentence level, but that's the idea.

## Installation

It is all intended to work with [llama.cpp](https://github.com/ggml-org/llama.cpp). The translation model can actually be any OpenAI endpoint, specified with an optional CLI argument, but the default assumption is a local llama.cpp server running at `http://localhost:8090/v1`.

### llama.cpp setup

You will need two separate llama.cpp servers running, one for the text part (e.g., translation, language identification) and one for the TTS part. There is little need for GPU on the text model; as long as there isn't much "thinking", it should be quite fast compared to the TTS part.

Text LLM example (Gemma 4 models are often good for translation):

```bash
./llama-server -m google_gemma-4-E4B-it-Q5_K_M.gguf --no-mmap -c 16000 --port 8090
```

TTS requires, specifically, downloading the [FP16 OuteTTS model](https://huggingface.co/OuteAI/Llama-OuteTTS-1.0-1B-GGUF/tree/main) and save it to the *tts_model* folder in this project. Then download *config.json*, *tokenizer.json*, and *tokenizer_config.json* [from here](https://huggingface.co/OuteAI/Llama-OuteTTS-1.0-1B/tree/main) and also save them to *tts_model*.

Then run the TTS llama.cpp server, ideally with GPU support, something like:

```bash
./llama-server -m /PATH/TO/tt2wice/tts_model/Llama-OuteTTS-1.0-1B-FP16.gguf -c 8192 --special --metrics --no-context-shift -ngl 999 --port 8091
```

I wouldn't touch any of the parameters except `ngl` and whatever else you need to do to get it running on your GPU. The port for this one is hardcoded to 8091 with no API key, because you'll need to use llama.cpp for this one for sure, so just do port 8091.

Note that no API key can be used for this. OuteTTS doesn't seem to know how to pass it, as far as I can tell.

### Python setup

Requires Python, `outetts`, `openai`, `torchcodec`, and `pandas` packages, and separately (non-Python) installation of FFmpeg (e.g., `dnf install ffmpeg`, `apt install ffmpeg`).

## Usage

See the command-line help:

```bash
python main.py -h
```

## TODO

Roughly in order of priority:

- [✓] Un-hardcode the LLM API URL and key
- [✓] Add support for specifying languages instead of hardcoded English/Dutch
- [✓] Track length of individual output chunks to check problems, e.g., when TTS produces a short output like "Nngggg" or "CSCHHHHHH" when it is supposed to actually say something
- [✓] Figure out what the actual required packages are (I think there were more), including for GPU
- [ ] Add title/author metadata to audio files
- [ ] Add chapter break metadata to output
- [ ] Translation could probably be improved with a better prompt that incorporates the context of the sentence/fragment
- [ ] Add support for other text sources than Project Gutenberg (and auto-detect the format)
