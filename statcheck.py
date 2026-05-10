# Check statistics of audio files to find any outliers that are probably wrong
import argparse
import os

import pandas as pd


def check_processed_csv(filename: str, big_ratio: float = None) -> None:
    df = pd.read_csv(filename)
    # Prevent scientific notation
    pd.set_option("display.float_format", "{:.3f}".format)

    # Check correlations
    print("Correlation between audio file sizes:")
    print(df.audio1_filesize.corr(df.audio2_filesize))
    print("Correlation between lang1 file size and text length:")
    print(df.audio1_filesize.corr(df.text.str.len()))
    print("Correlation between lang2 file size and text length:")
    print(df.audio2_filesize.corr(df.text.str.len()))

    # Normalize audio file sizes and text length, then check ratios
    audio1_fsnorm = (df.audio1_filesize / df.audio1_filesize.median()) / (
        df.text.str.len() / df.text.str.len().median()
    )
    audio2_fsnorm = (df.audio2_filesize / df.audio2_filesize.median()) / (
        df.translation.str.len() / df.translation.str.len().median()
    )
    normratio = pd.Series((audio1_fsnorm / audio2_fsnorm).values, index=df.chunk.values)
    print("Normalized audio1/audio2 ratio, audio1 is bigger:")
    print(normratio.sort_values(ascending=False).head(10))
    print("Normalized audio2/audio1 ratio, audio2 is bigger:")
    print((1 / normratio).sort_values(ascending=False).head(10))
    if big_ratio:
        rm1 = normratio[normratio > big_ratio].index
        for fname in df[df.chunk.isin(rm1)].audio1_path:
            print("rm", fname)
            try:
                os.remove(fname)
            except FileNotFoundError:
                print("    ^ not found, probably already deleted")
        print("Dropped audio1 > audio2 big ratio:", len(rm1))
        rm2 = normratio[(1 / normratio) > big_ratio].index
        for fname in df[df.chunk.isin(rm2)].audio2_path:
            print("rm", fname)
            try:
                os.remove(fname)
            except FileNotFoundError:
                print("    ^ not found, probably already deleted")
        print("Dropped audio2 > audio1 big ratio:", len(rm2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check for issues in a processed.csv file")
    ap.add_argument("processed_csv", help="Processed CSV file to check")
    ap.add_argument(
        "--rm-big-ratio",
        help="Remove rows with normalized audio2/audio1 ratio > 1.5 (and vice versa)",
        action="store_true",
    )
    args = ap.parse_args()
    big_ratio = 1.5 if args.rm_big_ratio else None
    check_processed_csv(args.processed_csv, big_ratio)
