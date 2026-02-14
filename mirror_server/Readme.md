# Mirror server

This is to be run in another server, that mirrors repositories from tamborg server.

It mirrors into a dedicated HDD partition, that the container automatically mounts and umounts.

## Setup

```sh
# - Partition HDD
sudo mkfs.ext4 -T largefile -m 0 /dev/sdXY
sudo mkdir /mnt/tamborg_mirror
sudo mount /dev/sdXY /mnt/tamborg_mirror
sudo chown 1000:1000 /mnt/tamborg_mirror
# - Copy repo/config to /mnt/tamborg_mirror/config
sudo umount /mnt/tamborg_mirror
# - Forward port 1701 in router

# cd to mirror_server

# Find destination in /dev/disk/by-partuuid/:
echo "PARTUUID=01234567-89ab-cdef-0123-456789abcdef" >.env

mkdir .ssh
chmod 700 .ssh
nano .ssh/authorized_keys
chmod 600 .ssh/authorized_keys
ssh-keygen -t ed25519 -f ssh_host_ed25519_key -N "" -C ""

docker compose up -d --build
```

Image assumes uid=1000, apply chown if not the case.

## Restore usage

`current/` (or `checked/` as a fallback) can be rsynced back to tamborg server's `data/`.

Alternatively, a folder with just `config` and `data/` is enough for a valid repo.

In any case, read https://borgbackup.readthedocs.io/en/stable/faq.html#can-i-copy-or-synchronize-my-repo-to-another-location before operating with it.
