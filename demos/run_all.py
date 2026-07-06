"""Run every demo, writing all artifacts to build/demo-output."""

import algorithms_visual
import gallery
import generators_zoo
import io_roundtrip
import layouts_gallery
import styling_showcase
from _common import output_dir

DEMOS = [
    layouts_gallery,
    styling_showcase,
    algorithms_visual,
    generators_zoo,
    io_roundtrip,
]


def main():
    out = output_dir()
    print(f"Writing demo output to {out}\n")
    for demo in DEMOS:
        demo.main()
        print()
    # Build the HTML gallery last, once every SVG has been written.
    gallery.main()
    count = len(list(out.glob("*")))
    print(f"\nDone. {count} files in {out}")
    print(f"Open {out / 'index.html'} to view the gallery.")


if __name__ == "__main__":
    main()
