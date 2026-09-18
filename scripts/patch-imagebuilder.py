#!/usr/bin/env python3
"""Work around an ImageBuilder bug that makes `make image` die in prepare_rootfs.

include/rootfs.mk emits `if [ -z "$(CONFIG_USE_APK)" ]; then $(if $(IB),,awk ...) ; ... fi`.
The image install sub-make runs with IB=1, so the awk collapses to nothing and the shell
gets `then  ;`, which is a syntax error even though the branch is dead (apk builds have
CONFIG_USE_APK=y). Inserting a no-op gives the branch a body.

Exits non-zero if neither the broken nor the patched form is found, so that an upstream
fix surfaces as a build failure here instead of being silently skipped.
"""

import pathlib
import sys

BROKEN = '\t\tif [ -z "$(CONFIG_USE_APK)" ]; then \\\n'
FIXED = '\t\tif [ -z "$(CONFIG_USE_APK)" ]; then :; \\\n'


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: patch-imagebuilder.py <imagebuilder-dir>")

    path = pathlib.Path(sys.argv[1]) / "include" / "rootfs.mk"
    text = path.read_text()

    if FIXED in text:
        print("rootfs.mk: already patched, nothing to do")
        return

    if BROKEN not in text:
        sys.exit(
            "ERROR: rootfs.mk does not contain the expected line. Upstream may have "
            "fixed this; drop this script and the workflow step that calls it."
        )

    path.write_text(text.replace(BROKEN, FIXED, 1))
    print("rootfs.mk: patched the empty then-branch in prepare_rootfs")


if __name__ == "__main__":
    main()
