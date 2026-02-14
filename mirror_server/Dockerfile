# FROM alpine:3.24
# RUN apk add --no-cache hpnssh rsync ... \

# hpnssh is currently only available in alpine edge
# TODO(2026-05): check if it made it into stable
FROM alpine:20260127

RUN apk add --no-cache --repository=http://dl-cdn.alpinelinux.org/alpine/edge/testing/ hpnssh \
  && apk add --no-cache \
    rsync \
    # Busybox's mount doesn't support "user"
    mount umount \
  && adduser -D mirror \
  # Fixes sshd "User mirror not allowed because account is locked":
  && passwd -u mirror \
  && adduser -D -h /run/hpnsshd -s /sbin/nologin -H -g "Privilege separated HPNSSH User" hpnsshd

CMD ["/cmd.sh"]
