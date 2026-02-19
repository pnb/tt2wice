import re


def chunk_para(txt: str, maxchars: int = 100, minchars: int = 10) -> [str]:
    """Recursively chunk a paragraph until chunks are a good length."""
    assert maxchars > 0
    txt = txt.strip()
    if not re.search(r"[a-zA-Z0-9]", txt):
        return []  # Only punctuation (although doesn't account for other languages)
    if len(txt) <= maxchars:
        return [txt]
    # Priority ordered regexes to split on, from most to least preferred
    ordered_regexes = [
        r"""[.!?]['"]*(?=[^.?!])""",
        r"([;—]+| – | -- |---|…)",
        r",",
        r"\s+",
    ]
    for rex in ordered_regexes:
        # Find match closest to center
        matches = list(
            m
            for m in re.finditer(rex, txt)
            if m.start() > minchars and m.end() < len(txt) - minchars
        )
        if matches:
            middle_match = min(matches, key=lambda m: abs(m.start() - len(txt) // 2))
            matchlen = middle_match.end() - middle_match.start()
            return [
                *chunk_para(txt[: middle_match.start() + matchlen], maxchars, minchars),
                *chunk_para(txt[middle_match.end() :], maxchars, minchars),
            ]
    # No matches at all
    print("Warning! Could not split text at all:", txt)
    return [txt]


def chunk_project_gutenberg(txt: str, maxchars: int = 100, minchars: int = 10) -> [str]:
    start_i = txt.index("*** START OF THE PROJECT GUTENBERG")
    start_i = txt.index("\n", start_i) + 1
    end_i = txt.rindex("*** END OF THE PROJECT GUTENBERG") - 1
    paragraphs = re.split(r"\n\n+", txt[start_i:end_i])
    chunks = []
    for i, para in enumerate(paragraphs):
        if i < 20 and (para.strip() in ["cover", "Contents"] or para == para.upper()):
            print("Skipping metadata paragraph", i + 1)
        elif len(para.strip()) == 0:
            print("Skipping blank paragraph", i + 1)
        else:
            para = re.sub(r"[‘’]", "'", para)
            para = re.sub(r"[“”]", '"', para)
            para = re.sub(r"(\s*\n\s*|\s\s+)", " ", para)  # Turn single \n into spaces
            para = re.sub(r"—+", " – ", para)  # Replace em dash(es) (can confuse TTS)
            chunks.extend(chunk_para(para, maxchars))
    return chunks


if __name__ == "__main__":
    print(chunk_para("This is one is too long but — it has em dash.", 40))
    print(chunk_para("This is one is too long but---it has triple hyphens.", 40))
    print(chunk_para("This is a sentence. This is another sentence.", 40))
    print(chunk_para("This is another sentence. This is a sentence.", 40))
    print(chunk_para("This is one is too long, can't be split on period.", 40))
    print(chunk_para("This one is too long with only a period at the end.", 40))
    print(chunk_para("This one is too long with an edge case of a semicolon;", 40))
    print(chunk_para("This one is too long with no punctuation at the end", 40))
    print(chunk_para("Short. A longer one here that should not split.", 40, 1))
    print(chunk_para('"Zwarte rook!" hoorde hij mensen roepen', 30))  # Group !"

    with open("pg36.txt", "r") as infile:
        pgchunks = chunk_project_gutenberg(infile.read(), 100)
    print(len(pgchunks), "PG chunks")
    minlen = min(len(c) for c in pgchunks)
    maxlen = max(len(c) for c in pgchunks)
    print("Min chunk length (chars):", minlen)
    print("Max chunk length (chars):", maxlen)
    print("Min-length chunk:", [c for c in pgchunks if len(c) == minlen][0])
    print("Max-length chunk:", [c for c in pgchunks if len(c) == maxlen][0])
    print("First and last 10 chunks:")
    print(pgchunks[:10])
    print("...")
    print(pgchunks[-10:])
