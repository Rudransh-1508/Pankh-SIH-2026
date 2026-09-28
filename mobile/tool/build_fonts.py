"""Build the app's bundled fonts from the official Google Fonts sources.

Usage (from mobile/): uv run --with fonttools --with brotli python tool/build_fonts.py

Fonts are bundled, not downloaded at runtime, so text renders correctly offline. Variable
sources are cut into the few static weights the app uses and subset to the scripts it shows,
which keeps the download small for low-end phones.
"""

import io
import urllib.parse
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).resolve().parent.parent / "assets" / "fonts"
REPO = "https://github.com/google/fonts/raw/main/ofl"

LATIN = "U+0000-00FF,U+0131,U+0152-0153,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20B9,U+2122,U+2190-2193,U+2212,U+2215"
DEVANAGARI = "U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+20B9,U+25CC,U+A830-A839,U+A8E0-A8FF"

FONTS = [
    # (source path, output family file prefix, weights, unicode ranges, extra axes to pin)
    ("baloo2/Baloo2[wght].ttf", "Baloo2", [500, 700], f"{LATIN},{DEVANAGARI}", {}),
    ("notosans/NotoSans[wdth,wght].ttf", "NotoSans", [400, 600, 700], LATIN, {"wdth": 100}),
    (
        "notosansdevanagari/NotoSansDevanagari[wdth,wght].ttf",
        "NotoSansDevanagari",
        [400, 600, 700],
        DEVANAGARI,
        {"wdth": 100},
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for path, family, weights, unicodes, pinned in FONTS:
        source = urllib.request.urlopen(f"{REPO}/{urllib.parse.quote(path)}").read()
        license_text = urllib.request.urlopen(f"{REPO}/{path.split('/')[0]}/OFL.txt").read()
        (OUT / f"{family}-OFL.txt").write_bytes(license_text)
        for weight in weights:
            font = TTFont(io.BytesIO(source))
            static = instancer.instantiateVariableFont(font, {"wght": weight, **pinned})
            options = subset.Options()
            options.layout_features = ["*"]
            options.name_IDs = ["*"]
            subsetter = subset.Subsetter(options)
            subsetter.populate(unicodes=subset.parse_unicodes(unicodes))
            subsetter.subset(static)
            target = OUT / f"{family}-{weight}.ttf"
            static.save(target)
            print(f"{target.name}: {target.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
