#!/bin/bash
set -euo pipefail

get_val() {
  sed -r 's/.+: +//'
}

target=$(findmnt --noheadings --output source "$1")
tune_list=$(tune2fs -l "$target")
blksz=$(echo "$tune_list" | grep "Block size:" | get_val)
reserved=$(echo "$tune_list" | grep "Reserved block count:" | get_val)

echo $(( reserved * blksz )) | numfmt --to=iec
