# Check statistics of audio files to find any outliers that are probably wrong
import argparse

import pandas as pd
from scipy import stats


def check_processed_csv(filename: str) -> None:
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
    # Find biggest outliers
    diff = df.audio2_filesize - predicted2
    print("Largest outliers in file size:")
    print(diff.sort_values(ascending=False).head(10))
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Check for issues in a processed.csv file")
    ap.add_argument("processed_csv", help="Processed CSV file to check")
    args = ap.parse_args()
    check_processed_csv(args.processed_csv)
