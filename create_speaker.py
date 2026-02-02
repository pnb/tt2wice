import argparse

import outetts

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("wav_file", type=str, help="Path to the speech WAV (6-10 seconds)")
    ap.add_argument("out_json_file", type=str, help="Path to the output JSON file")
    args = ap.parse_args()

    print("Initializing TTS")
    interface = outetts.Interface(
        config=outetts.ModelConfig.auto_config(
            model=outetts.Models.VERSION_1_0_SIZE_1B,
            backend=outetts.Backend.LLAMACPP,
            quantization=outetts.LlamaCppQuantization.FP16,
        )
    )

    print("Creating speaker")
    speaker = interface.create_speaker(args.wav_file)
    print("Saving speaker JSON file")
    interface.save_speaker(speaker, args.out_json_file)
