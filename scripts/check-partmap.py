#!/usr/bin/env python3
"""Fail the build unless the image's partition table matches the target router's disk.

sysupgrade compares the image's partition map against the disk's. When they differ it
rewrites the whole disk, which drops any partition beyond the rootfs. This reproduces
sysupgrade's own GPT arithmetic (see get_partitions in /lib/upgrade/common.sh) so a
mismatch fails here instead of on the router.
"""

import argparse
import gzip
import struct
import sys

SECTOR = 512


def read_header(path, sectors=34):
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as fh:
        return fh.read(sectors * SECTOR)


def partmap(head):
    if head[510:512] != b"\x55\xaa":
        sys.exit("ERROR: no MBR boot signature, not a disk image")
    if head[SECTOR : SECTOR + 8] != b"EFI PART":
        sys.exit("ERROR: no GPT header, this check only handles EFI images")

    entries = []
    for num in range(1, 16):
        offset = 0x380 + num * 0x80
        entry = head[offset : offset + 0x80]
        if entry[:16] == b"\x00" * 16:
            continue
        first, last = struct.unpack_from("<QQ", entry, 32)
        entries.append((num, first, last - first + 1))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--kernel-mb", type=int, required=True)
    ap.add_argument("--rootfs-mb", type=int, required=True)
    args = ap.parse_args()

    kernel_sectors = args.kernel_mb * 2048
    rootfs_sectors = args.rootfs_mb * 2048
    expected = [(1, 512, kernel_sectors), (2, 512 + kernel_sectors, rootfs_sectors)]

    actual = partmap(read_header(args.image))

    def show(rows):
        return "\n".join("  %2d %9d %10d" % row for row in rows)

    print("expected (part, start, sectors):\n%s" % show(expected))
    print("actual:\n%s" % show(actual))

    if actual != expected:
        sys.exit(
            "\nERROR: partition map mismatch. Flashing this image would make sysupgrade "
            "rewrite the whole disk and drop /opt."
        )
    print("\nOK: partition map matches the router, sysupgrade will write per partition.")


if __name__ == "__main__":
    main()
