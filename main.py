import argparse
import csv
import glob
import os

import openai
import supertonic

import textload
import statcheck

# ISO code -> English name, for the languages Supertonic supports
LANG_NAMES = {
    "ar": "Arabic",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "cs": "Czech",
    "da": "Danish",
    "nl": "Dutch",
    "en": "English",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "de": "German",
    "el": "Greek",
    "hi": "Hindi",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "es": "Spanish",
    "sv": "Swedish",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
}

VOICES = {f"{group}{i}" for group in "MF" for i in range(1, 6)}


class SupertonicTTS:
    def __init__(self, voice1: str, voice2: str):
        # First run downloads the model into ~/.cache/supertonic3/
        self.tts = supertonic.TTS(auto_download=True)
        self.voice1 = self.tts.get_voice_style(voice_name=voice1)
        self.voice2 = self.tts.get_voice_style(voice_name=voice2)

    def generate(self, text: str, lang: str, use_voice2: bool, out_path: str):
        wav, _ = self.tts.synthesize(
            text=text,
            voice_style=self.voice2 if use_voice2 else self.voice1,
            lang=lang,
        )
        self.tts.save_audio(wav, out_path)


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
    print("Probably check the statistics about chunk length:")
    print("\tpython statcheck.py", os.path.join(args.out_dir, "processed.csv"))
    print("Hopefully the correlations will be close to .85 or higher.")
    print(
        "Usually it is also good to do statcheck with --rm-big-ratio and rerun main.py "
        "to regenerate the problematic chunks. Some will never be fixed, so 1-2 times "
        "is as good as it will get."
    )
    print("Finally, consider converting to mono MP3 like:")
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
            {
                "role": "user",
                "content": text,
            },
        ],
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dual-language audiobook generator")
    ap.add_argument("text_file", help="Input text file (book)")
    ap.add_argument("out_dir", help="Output directory")
    ap.add_argument(
        "--voice1",
        default="M5",
        help="Supertonic voice for the original text, M1-M5 or F1-F5 (default M5)",
    )
    ap.add_argument(
        "--voice2",
        default="F3",
        help="Supertonic voice for the translation, M1-M5 or F1-F5 (default F3)",
    )
    ap.add_argument(
        "--trans-lang",
        default="nl",
        help="Translation language, ISO code (e.g. nl, es, fr) (default nl)",
    )
    ap.add_argument(
        "--api-url-translation",
        help="Translation LLM URL (OpenAI-compatible; default http://localhost:8090)",
        default="http://localhost:8090",
    )
    ap.add_argument("--api-key-translation", help="API key for translation LLM")
    ap.add_argument(
        "--concat-only",
        action="store_true",
        help="Skip the actual TTS part and create an output file from whatever has "
        "been processed so far (for creating an incomplete audiobook and/or for "
        "testing)",
    )
    args = ap.parse_args()
    if args.voice1 not in VOICES or args.voice2 not in VOICES:
        ap.error(f"Invalid voice, must be one of {sorted(VOICES)}")
    if args.trans_lang not in LANG_NAMES:
        ap.error(f"Invalid --trans-lang, must be one of {sorted(LANG_NAMES)}")
    if args.concat_only:
        concat_audio(args.out_dir)
        exit()
    with open(args.text_file, "r") as infile:
        text = infile.read()
    if "Project Gutenberg" not in text[:50]:
        print("Error: Text format not detected (only Project Gutenberg supported)")
        exit(1)

    print("Initializing TTS engine...")
    tts = SupertonicTTS(args.voice1, args.voice2)
    print("Chunking text...")
    chunks = textload.chunk_project_gutenberg(text, 100)
    print(len(chunks), "chunks")

    openai.api_key = args.api_key_translation if args.api_key_translation else "NONE"
    openai.base_url = args.api_url_translation.rstrip("/") + "/v1/"

    print("Detecting language of text...")
    text_lang = detect_language(" ".join(chunks[:5]))
    print("Detected language:", text_lang)
    trans_lang_name = LANG_NAMES[args.trans_lang]
    # Map the detected language name to an ISO code for Supertonic; if the LLM
    # returns something unexpected, fall back to language-agnostic mode
    text_lang_code = next(
        (c for c, n in LANG_NAMES.items() if n.lower() == text_lang.lower()), "na"
    )
    if text_lang_code == "na":
        print("Warning: detected language not supported by Supertonic, using 'na'")

    os.makedirs(args.out_dir, exist_ok=True)

    # Load the processing tracking file if it exists
    tracking_info = []
    tracking_info_fname = os.path.join(args.out_dir, "processed.csv")
    try:
        with open(tracking_info_fname) as infile:
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
        elif i <= len(tracking_info):  # Maybe file was deleted for regen
            for j, ti in enumerate(tracking_info):
                if int(ti["chunk"]) == i:
                    print("Removing tracking info row for chunk", i, "(file gone)")
                    # Remove tracking info file to trigger full rewrite of file
                    os.remove(tracking_info_fname)
                    del tracking_info[j]
                    break

        print("Generating audio for chunk", i, "/", len(chunks) - 1)
        # Translate the text
        prompt = (
            f"Translate the following {text_lang} text fragment to "
            f"{trans_lang_name}:\n\n" + chunk
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
                    {
                        "role": "user",
                        "content": prompt,
                    },
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
        # Generate the audio files: lang1 is the original text, lang2 the translation
        tts.generate(chunk, text_lang_code, False, audio1_path)
        tts.generate(chunk_translated, args.trans_lang, True, audio2_path)

        # Keep track of some stats so we can figure out where things go wrong, such as
        # bad translations or audio generation failures
        tracking_info.append(
            {
                "chunk": i,
                "audio1_path": audio1_path,
                "audio2_path": audio2_path,
                "audio1_filesize": os.path.getsize(audio1_path),
                "audio2_filesize": os.path.getsize(audio2_path),
                "text_lang": text_lang,
                "trans_lang": trans_lang_name,
                "text": chunk,
                "translation": chunk_translated,
            }
        )
        if not os.path.exists(tracking_info_fname):
            # First row OR the whole thing was deleted to trigger full rewrite of file
            with open(tracking_info_fname, "w") as ofile:
                writer = csv.DictWriter(ofile, fieldnames=tracking_info[0].keys())
                writer.writeheader()
                for row in tracking_info:
                    writer.writerow(row)
        else:
            with open(tracking_info_fname, "a") as ofile:
                writer = csv.DictWriter(ofile, fieldnames=tracking_info[0].keys())
                writer.writerow(tracking_info[-1])

    statcheck.check_processed_csv(os.path.join(args.out_dir, "processed.csv"))
    concat_audio(args.out_dir)
