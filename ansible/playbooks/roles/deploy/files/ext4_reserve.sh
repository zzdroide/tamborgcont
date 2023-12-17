#!/bin/bash
set -euo pipefail

get_val() {
  sed -r 's/.+: +//'
}

reserve_size=$(numfmt --from=iec "$1")
target=$(findmnt --noheadings --output source "$2")
tune_list=$(tune2fs -l "$target")
blksz=$(echo "$tune_list" | grep "Block size:" | get_val)
reserve_blocks=$(( reserve_size / blksz ))

tune2fs -r $reserve_blocks "$target"
