import argparse
import glob
import os
import wave

import textload

from tqdm import tqdm
import outetts
import openai


class OuteTTS:
    def __init__(self):
        # Initialize the interface
        self.interface = outetts.Interface(
            config=outetts.ModelConfig.auto_config(
                model=outetts.Models.VERSION_1_0_SIZE_1B,
                backend=outetts.Backend.LLAMACPP,
                quantization=outetts.LlamaCppQuantization.FP16,
            )
        )
        self.speakers = {}
        self.speakers["en"] = self.interface.load_default_speaker("EN-FEMALE-1-NEUTRAL")
        self.speakers["nl"] = self.interface.load_speaker(
            os.path.join("speakers", "librivox-schoolmeester-nl.json")
        )

    def generate(self, text: str, lang: str):
        output = self.interface.generate(
            config=outetts.GenerationConfig(
                text=text,
                speaker=self.speakers[lang],
            )
        )
        return output


def concat_audio(output_file: str, lang1: str, lang2: str):
    # Concat the audio files
    with wave.open(output_file, "wb") as outfile:
        lang1_files = sorted(glob.glob(os.path.join("tmp", f"*-{lang1}.wav")))
        lang2_files = sorted(glob.glob(os.path.join("tmp", f"*-{lang2}.wav")))
        for i, (lang1_file, lang2_file) in enumerate(zip(lang1_files, lang2_files)):
            print(lang1_file, lang2_file)
            assert (
                os.path.basename(lang1_file).split("-")[0]
                == os.path.basename(lang2_file).split("-")[0]
            ), "Audio files do not match between languages"
            with wave.open(lang1_file, "rb") as infile:
                if i == 0:
                    outfile.setparams(infile.getparams())
                outfile.writeframes(infile.readframes(infile.getnframes()))
            with wave.open(lang2_file, "rb") as infile:
                outfile.writeframes(infile.readframes(infile.getnframes()))
    print("Done!")
    print("Consider converting to mono MP3 like:")
    print("\tffmpeg -i book.wav -vn -ac 1 -b:a 192k book.mp3")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Dual-language audiobook generator")
    ap.add_argument("text_file", help="Input text file (book)")
    ap.add_argument("output_file", help="Output audio file")
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
    # TODO: First language, second language args
    args = ap.parse_args()
    if not args.pg:
        print("Only Project Gutenberg books supported for now")
        exit(1)
    if args.concat_only:
        concat_audio(args.output_file, "en", "nl")
        exit()
    with open(args.text_file, "r") as infile:
        text = infile.read()

    print("Initializing TTS engine...")
    tts = OuteTTS()
    print("Chunking text...")
    chunks = textload.chunk_project_gutenberg(text, 100)
    print(len(chunks), "chunks")

    openai.api_key = "some-key"
    openai.base_url = "http://localhost:8090/v1/"

    for i, chunk in enumerate(chunks):
        audio1_path = os.path.join("tmp", f"{i:08d}-en.wav")
        audio2_path = os.path.join("tmp", f"{i:08d}-nl.wav")
        if os.path.exists(audio1_path) and os.path.exists(audio2_path):
            print("Skipping already-completed chunk", i)
            continue
        print("Generating audio for chunk", i, "/", len(chunks) - 1)
        # Translate the text
        prompt = "Translate the following English text fragment to Dutch:\n\n" + chunk
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
        # Generate the Dutch audio
        audio1 = tts.generate(chunk, "en")
        audio2 = tts.generate(chunk_translated, "nl")
        audio1.save(audio1_path)
        audio2.save(audio2_path)

    concat_audio(args.output_file, "en", "nl")
