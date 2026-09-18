#!/usr/bin/env python3
"""Prepare the ImageBuilder: fix a shell bug and drop image formats we do not flash.

1. include/rootfs.mk emits `if [ -z "$(CONFIG_USE_APK)" ]; then $(if $(IB),,awk ...) ; ... fi`.
   The image install sub-make runs with IB=1, so that $(if) collapses to nothing and the
   shell is handed `then  ;`, a syntax error even though the branch is dead on apk builds
   (CONFIG_USE_APK=y). Giving the $(if) a `:` in its IB branch keeps the emitted line valid
   without changing what a real source build does.

2. The x86 target also builds ISO, qcow2, VDI, VMDK and VHDX variants, which need extra
   host tools (mkisofs, qemu-img) and several minutes. Only the raw combined EFI image
   gets flashed, so the rest are switched off in .config.
"""

import pathlib
import sys

BROKEN = "\t\t\t$(if $(IB),,awk -i inplace \\\n"
FIXED = "\t\t\t$(if $(IB),:,awk -i inplace \\\n"

DROP_FORMATS = ["ISO", "QCOW2", "VDI", "VMDK", "VHDX"]


def patch_rootfs_mk(root):
    path = root / "include" / "rootfs.mk"
    text = path.read_text()

    if FIXED in text:
        print("rootfs.mk: already patched")
        return

    if BROKEN not in text:
        sys.exit(
            "ERROR: rootfs.mk does not contain the expected line. Upstream may have "
            "fixed this; drop this part of the script."
        )

    path.write_text(text.replace(BROKEN, FIXED, 1))
    print("rootfs.mk: gave the IB branch of prepare_rootfs a no-op body")


def trim_image_formats(root):
    path = root / ".config"
    text = path.read_text()

    for name in DROP_FORMATS:
        enabled = "CONFIG_%s_IMAGES=y\n" % name
        disabled = "# CONFIG_%s_IMAGES is not set\n" % name
        if enabled in text:
            text = text.replace(enabled, disabled, 1)
            print(".config: disabled %s images" % name)
        elif disabled in text:
            print(".config: %s images already disabled" % name)
        else:
            print(".config: no %s switch found, leaving it alone" % name)

    path.write_text(text)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: patch-imagebuilder.py <imagebuilder-dir>")

    root = pathlib.Path(sys.argv[1])
    patch_rootfs_mk(root)
    trim_image_formats(root)


if __name__ == "__main__":
    main()
