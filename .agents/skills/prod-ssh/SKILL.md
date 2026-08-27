---
name: prod-ssh
description: Run commands on the live tamborg backup server via ./prod_ssh.sh (SSH ControlMaster).
disable-model-invocation: true
---

# prod-ssh

## Human setup

SSH authentication is interactive. The agent cannot log in. Establish the mux with:

```sh
./prod_ssh.sh --setup [--user USER]
```

## Agent: how to run commands

Run `./prod_ssh.sh` from the repo root. Each invocation checks the mux and
runs the given command as `borg` (login shell, cwd `/home/borg`). If the mux
is down, tell the human to run `./prod_ssh.sh --setup` and **stop**.

```sh
./prod_ssh.sh -- ls TAM
./prod_ssh.sh -- journalctl --user -n 50 --no-pager -u borg-daily.service
```

## Quoting

The arguments are joined with spaces into a single command that `zsh` parses on
the server, exactly like plain `ssh`. Your local shell strips one level of
quotes, so whatever the *server* must see quoted needs a second level:

```sh
./prod_ssh.sh -- ls "env/*"                                   # glob expands on the server
./prod_ssh.sh -- curl -sS -w '"%{http_code}\n"' http://127.0.0.1:8087/TAM
```

Without that second level, `-w "%{http_code}\n"` arrives as three words and
curl treats `http` as a URL.

For arguments containing spaces, `$vars`, `;`, pipes or several lines, pass the
whole script as one single-quoted argument:

```sh
./prod_ssh.sh -- 'pid=189727
for t in /proc/$pid/task/*; do echo "$t $(<$t/comm)"; done'
```

The script is sent on stdin, so no intermediate shell re-parses it and
newlines, `$`, quotes and `;` reach `zsh` verbatim. The flip side is that stdin
is taken: you cannot pipe local data into the remote command.

## Safety

Read-only unless the user asked to change something. Do not prune, compact,
`borg delete`, edit `config.yml` / `~/env/*`, restart services, or run
`update_authorized_keys.sh` without an explicit request. Do not print
passphrases from `~/env/`.
