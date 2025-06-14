#!/usr/bin/env bash
set -euo pipefail

# GNU find:
find . -type f ! -iname '*.bmp' -print -delete
