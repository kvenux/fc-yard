#!/bin/sh
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 serve.py
fi
echo 'Python 3 is required on macOS/Linux. Install Python 3, then run this script again.'
exit 1
