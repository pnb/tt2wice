# Check statistics of audio files to find any outliers that are probably wrong
import argparse
import os

import pandas as pd
from scipy import stats
from tqdm import tqdm


def check_processed_csv(filename: str, big_ratio: float = None) -> None:
    df = pd.read_csv(filename)
    # Prevent scientific notation
    pd.set_option("display.float_format", "{:.2f}".format)

    # Check correlations
    print("Correlation between audio file sizes:")
    print(df.audio1_filesize.corr(df.audio2_filesize))
    print("Correlation between lang1 file size and text length:")
    print(df.audio1_filesize.corr(df.text.str.len()))
    print("Correlation between lang2 file size and text length:")
    print(df.audio2_filesize.corr(df.text.str.len()))

    # Do a linear regression of audio1 size vs audio2 size, then predict the audio2 size
    # for each audio1 size, and see how far off the actual audio2 size is
    slope, intercept, r, p, se = stats.linregress(
        df.audio1_filesize, df.audio2_filesize
    )
    predicted2 = slope * df.audio1_filesize + intercept
    print(predicted2, "---- Actual:", df.audio2_filesize)
    # Find biggest outliers
    diff = df.audio2_filesize - predicted2
    print("Audio2 bigger than expected from audio1:")
    print(diff.sort_values(ascending=False).head(10))
    print("Audio2 smaller than expected from audio1:")
    print(diff.sort_values(ascending=True).head(10))

    # Also try find outliers in text length vs audio size
    slope, intercept, r, p, se = stats.linregress(df.text.str.len(), df.audio1_filesize)
    predicted1 = slope * df.text.str.len() + intercept
    diff = df.audio1_filesize - predicted1
    print("Largest outliers in audio1 file size vs text length:")
    print(diff.sort_values(ascending=False).head(10))
    print(diff.sort_values(ascending=True).head(10))
    slope, intercept, r, p, se = stats.linregress(df.text.str.len(), df.audio2_filesize)
    predicted2 = slope * df.text.str.len() + intercept
    diff = df.audio2_filesize - predicted2
    print("Largest outliers in audio2 file size vs text length:")
    print(diff.sort_values(ascending=False).head(10))
    print(diff.sort_values(ascending=True).head(10))
    # TODO: Ideally this would check outliers in translation text length, and then match
    # the translation 1/2 to audio 1/2 to check the correct text length against size.

    # Also check ratio of file sizes
    print("Audio2/Audio1 ratio, audio2 is bigger:")
    ratio = pd.Series(
        (df.audio2_filesize / df.audio1_filesize).values, index=df.chunk.values
    )
    print(ratio.sort_values(ascending=False).head(10))
    print("Audio2/Audio1 ratio, audio1 is bigger:")
    print(ratio.sort_values(ascending=True).head(10))
    if big_ratio:
        rm1 = df[df.audio2_filesize > big_ratio * df.audio1_filesize]
        for fname in tqdm(rm1.audio1_path):
            os.remove(fname)
        print("Dropped audio2 > audio1 big ratio:", len(rm1))
        rm2 = df[df.audio1_filesize > big_ratio * df.audio2_filesize]
        for fname in tqdm(rm2.audio2_path):
            os.remove(fname)
        print("Dropped audio1 > audio2 big ratio:", len(rm2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check for issues in a processed.csv file")
    ap.add_argument("processed_csv", help="Processed CSV file to check")
    ap.add_argument(
        "--rm-big-ratio",
        help="Remove rows with audio2/audio1 ratio > 1.25 (and vice versa)",
        action="store_true",
    )
    args = ap.parse_args()
    big_ratio = 1.25 if args.rm_big_ratio else None
    check_processed_csv(args.processed_csv, big_ratio)
