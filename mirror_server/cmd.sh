#!/bin/sh
set -eu

echo "/dev/disk/by-partuuid/${PARTUUID} /mnt/tamborg_mirror ext4 noauto,users" >/etc/fstab
# Unmount if it was left mounted, so that it can spindown:
umount /mnt/tamborg_mirror || true

exec /usr/sbin/hpnsshd -De
