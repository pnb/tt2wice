import argparse
import csv
import glob
import json
import os
import warnings

from tqdm import tqdm
import outetts
import openai

import textload
import statcheck


class OuteTTS:
    def __init__(self, lang1_speaker_file: str, lang2_speaker_file: str):
        # Initialize the interface
        self.interface = outetts.Interface(
            config=outetts.ModelConfig.auto_config(
                model=outetts.Models.VERSION_1_0_SIZE_1B,
                backend=outetts.Backend.LLAMACPP,
                quantization=outetts.LlamaCppQuantization.FP16,
            )
        )
        self.speaker1 = self.interface.load_speaker(lang1_speaker_file)
        self.speaker2 = self.interface.load_speaker(lang2_speaker_file)

    def generate(self, text: str, use_lang2: bool):
        output = self.interface.generate(
            config=outetts.GenerationConfig(
                text=text,
                speaker=self.speaker2 if use_lang2 else self.speaker1,
            )
        )
        return output


def concat_audio(audio_dir: str):
    # Concat the audio files, or at least set up FFmpeg for it. Concatenating WAVs alone
    # does not work because the output can easily exceed 4GB (limit of `wave` std lib).
    # TODO: auto-extract author and title, and add as metadata via ffmpeg:
    #   -metadata title="Blah" -metadata artist="Blah"
    out_fname = os.path.join(audio_dir, "ffmpeg-list.txt")
    with open(out_fname, "w") as ofile:
        lang1_files = sorted(glob.glob(os.path.join(audio_dir, "*-lang1.wav")))
        lang2_files = sorted(glob.glob(os.path.join(audio_dir, "*-lang2.wav")))
        for i, (lang1_file, lang2_file) in enumerate(zip(lang1_files, lang2_files)):
            assert (
                os.path.basename(lang1_file).split("-")[0]
                == os.path.basename(lang2_file).split("-")[0]
            ), f"Audio files do not match between languages: {lang1_file}, {lang2_file}"
            ofile.write("file '" + os.path.basename(lang1_file) + "'\n")
            ofile.write("file '" + os.path.basename(lang2_file) + "'\n")
    print("Wrote file list to", out_fname)
    print("Consider converting to mono MP3 like:")
    print("\tffmpeg -f concat -i", out_fname, "-ac 1 -b:a 192k book.mp3")


def detect_language(text: str) -> str:
    sysprompt = (
        "You are a language detection assistant. You are given a text fragment and you "
        "must determine the language of the text. You must respond with the language "
        "name in English, e.g. 'English', 'Dutch', 'French', etc.\n"
        "NEVER include any extra text or explanations, just the language name."
    )
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": sysprompt,
            },
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    # Ignore some TTS warnings that don't seem to matter
    warnings.filterwarnings("ignore", message=".*The.*parameter.*by TorchCodec.*")
    warnings.filterwarnings("ignore", message=".*Possible clipped samples in output.*")

    ap = argparse.ArgumentParser(description="Dual-language audiobook generator")
    ap.add_argument("speaker1_json", help="Speaker JSON file for first language")
    ap.add_argument("speaker2_json", help="Speaker JSON file for second language")
    ap.add_argument("text_file", help="Input text file (book)")
    ap.add_argument("out_dir", help="Output directory")
    ap.add_argument(
        "--api-url-translation",
        help="Translation LLM URL (OpenAI-compatible; default http://localhost:8080)",
        default="http://localhost:8080",
    )
    ap.add_argument("--api-key-translation", help="API key for translation LLM")
    ap.add_argument(
        "--pg", action="store_true", help="Input is a Project Gutenberg book"
    )
    ap.add_argument(
        "--concat-only",
        action="store_true",
        help="Skip the actual TTS part and create an output file from whatever has "
        "been processed so far (for creating an incomplete audiobook and/or for "
        "testing)",
    )
    args = ap.parse_args()
    if not args.pg:
        print("Only Project Gutenberg books supported for now")
        exit(1)
    if args.concat_only:
        concat_audio(args.out_dir)
        exit()
    with open(args.text_file, "r") as infile:
        text = infile.read()

    print("Initializing TTS engine...")
    tts = OuteTTS(args.speaker1_json, args.speaker2_json)
    print("Chunking text...")
    chunks = textload.chunk_project_gutenberg(text, 100)
    print(len(chunks), "chunks")

    openai.api_key = args.api_key_translation if args.api_key_translation else "NONE"
    openai.base_url = args.api_url_translation.rstrip("/") + "/v1/"

    print("Detecting language of text...")
    text_lang = detect_language(" ".join(chunks[:5]))
    print("Detected language:", text_lang)

    print("Detecting speaker languages...")
    with open(args.speaker1_json, "r") as infile:
        speaker1 = json.load(infile)
    speaker1_lang = detect_language(speaker1["text"])
    with open(args.speaker2_json, "r") as infile:
        speaker2 = json.load(infile)
    speaker2_lang = detect_language(speaker2["text"])
    print("Speaker languages:", [speaker1_lang, speaker2_lang])
    if speaker1_lang != text_lang and speaker2_lang != text_lang:
        print("Error: Neither speaker JSON file seems to match the text language")
        exit(1)
    trans_lang = speaker1_lang if speaker1_lang != text_lang else speaker2_lang

    os.makedirs(args.out_dir, exist_ok=True)

    # Load the processing tracking file if it exists
    tracking_info = []
    try:
        with open(os.path.join(args.out_dir, "processed.csv")) as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                tracking_info.append(row)
    except FileNotFoundError:
        pass  # Expected, no tracking file yet

    for i, chunk in enumerate(chunks):
        audio1_path = os.path.join(args.out_dir, f"{i:08d}-lang1.wav")
        audio2_path = os.path.join(args.out_dir, f"{i:08d}-lang2.wav")
        if os.path.exists(audio1_path) and os.path.exists(audio2_path):
            print("Skipping already-completed chunk", i, "/", len(chunks))
            continue
        print("Generating audio for chunk", i, "/", len(chunks) - 1)
        # Translate the text
        prompt = (
            f"Translate the following {text_lang} text fragment to {trans_lang}:\n\n"
            + chunk
        )
        for temperature in [0.3, 0.5, 0.9, 0.6, 1.0, 1.2] * 2:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a translation assistant. You provide "
                        "translations, and you never include any extra text or "
                        "explanations, just the translation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            chunk_translated = response.choices[0].message.content.strip()
            if "\n" not in chunk_translated:
                break
            print("Retry with different temperature (invalid translation)")
            print(chunk_translated)
        else:
            print("Translation failed!")
            print("English:", chunk)
            print("Last translation attempt:", chunk_translated)
            exit(1)
        print(chunk)
        print(chunk_translated)
        # Generate the audio files for both languages
        if text_lang == speaker1_lang:
            audio1 = tts.generate(chunk, False)
            audio2 = tts.generate(chunk_translated, True)
        else:
            audio1 = tts.generate(chunk_translated, False)
            audio2 = tts.generate(chunk, True)
        audio1.save(audio1_path)
        audio2.save(audio2_path)

        # Keep track of some stats so we can figure out where things go wrong, such as
        # bad translations or audio generation failures
        tracking_info.append(
            {
                "chunk": i,
                "audio1": audio1_path,
                "audio1": audio2_path,
                "audio1_filesize": os.path.getsize(audio1_path),
                "audio2_filesize": os.path.getsize(audio2_path),
                "text_lang": text_lang,
                "trans_lang": trans_lang,
                "speaker1_lang": speaker1_lang,
                "speaker2_lang": speaker2_lang,
                "text": chunk,
                "translation": chunk_translated,
            }
        )
        with open(os.path.join(args.out_dir, "processed.csv"), "a") as ofile:
            writer = csv.DictWriter(ofile, fieldnames=tracking_info[0].keys())
            if len(tracking_info) == 1:  # First time
                writer.writeheader()
            writer.writerow(tracking_info[-1])

    statcheck.check_processed_csv(os.path.join(args.out_dir, "processed.csv"))
    concat_audio(args.out_dir)
