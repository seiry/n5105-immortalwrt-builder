# n5105 ImmortalWrt builder

Builds an ImmortalWrt x86/64 image for the `n5105` router with its packages already
baked in, including the ones from third-party feeds that the official sysupgrade
service cannot see.

Run it from the Actions tab (`Build image` → `Run workflow`), or let the weekly
schedule rebuild it. The image lands as a workflow artifact.

## Why this exists instead of attended sysupgrade

Two reasons, both learned the hard way.

**The partition table must match.** This router's disk is `p1` 32 MiB boot, `p2` 4 GiB
rootfs, `p3` 234 GiB ext4 on `/opt` holding the Docker data. Stock images ship a 300 MB
rootfs, so the partition maps differ, and `platform_do_upgrade` then takes its
full-disk `dd` branch: the GPT is rewritten to two partitions and `p3` disappears from
it. `sysupgrade` runs with `INTERACTIVE=0`, so the "Partition layout has changed"
prompt answers itself and the flash proceeds without asking. The build therefore pins
`ROOTFS_PARTSIZE=4096`, and `scripts/check-partmap.py` fails the job if the image that
comes out does not match the disk sector for sector.

**Third-party packages.** `luci-app-nikki` comes from a feed the ImmortalWrt build
server does not have, so an attended sysupgrade build either fails or silently drops
it. Here the feed is added to the ImageBuilder directly, so nikki is in the image.

The attended sysupgrade service also has a 600 second job timeout, which a 4 GiB rootfs
build does not reliably fit into. This has no timeout worth worrying about.

## Layout

| Path | What it is |
| --- | --- |
| `config/packages.txt` | Packages to install. A leading `-` removes a default. |
| `config/repositories.extra` | Extra apk feeds, one URL per line. |
| `keys/*.pem` | Public keys for those feeds, copied into the ImageBuilder. |
| `files/` | Files copied into the image as-is, rooted at `/`. |
| `scripts/check-partmap.py` | The partition-table gate. |

To regenerate the package list from the running router:

```sh
ssh root@192.168.9.1 'owut list'
```

## Flashing

Download and unpack the artifact, then copy the image to the router:

```sh
scp -O immortalwrt-*-squashfs-combined-efi.img.gz root@192.168.9.1:/tmp/
```

On the router:

```sh
sysupgrade --create-backup /tmp/backup-$(date +%F).tar.gz   # copy this off the box
/etc/init.d/dockerd stop
sysupgrade -T /tmp/immortalwrt-*-squashfs-combined-efi.img.gz
```

The dry run must not print `Partition layout has changed`. If it does, stop: the image
does not match the disk and flashing it would take `/opt` with it. Otherwise:

```sh
sysupgrade /tmp/immortalwrt-*-squashfs-combined-efi.img.gz
```

The box reboots into the new image with `/etc` restored from the backup that sysupgrade
stashes on the boot partition. Check `df -h /opt` afterwards to confirm the Docker
partition came back, then `/etc/init.d/dockerd start`.

## If the partition table ever gets rewritten anyway

The data survives: the image is a few hundred MB and `p3` starts at 4 GiB, so only the
GPT entry is lost, not the bytes. Rebuild the entry with

```sh
sgdisk -n 3:8456192:+491661312 -t 3:8300 /dev/nvme0n1
```
