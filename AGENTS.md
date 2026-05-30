# tamborgcont (tam-borg-control)
This repository contains the server part of the client-server backup system with Borg Backup.

It has 4 main components:

## Ansible deployment
Every computer in the system is backed up, except for the server itself. It has to be simple to restore if it fails, so its deployment is automated with Ansible.

The deployment role is located in `ansible/playbooks/roles/deploy/`, and its Molecule tests in `ansible/molecule/default/`. Because the tests use a VirtualBox VM which is stateful, you should ask a human to run them for you.

There's a linter that is run with `cd ansible && poetry run ansible-lint`. It takes some seconds to run though so try to batch changes before running it.

## Hook
The traditional Borg security model is that the clients are more trusted than the server. Here it's the other way around, so every time a client connects and disconnects, the hook checks if it behaved maliciously.

Its code is mostly located in `hook/`, and its tests in `tests/`. They run quite fast, so there's no harm in running them with `poetry run pytest`.

## Daily
Because only one client can backup to a repo at the same time, there's a daily cron in the server that orchestrates the backup clients. Its code is mostly located in `daily/`, and is optimistic so it has no tests.

## Shared
Code shared between Hook and Daily, located in `shared/`. If you're working in Daily but you edit files in Shared, run Hook tests.
