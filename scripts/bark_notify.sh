#!/usr/bin/env bash
# Kept so existing callers keep working: same flags as before
# (--title --body [--sound --group --level --url]) plus everything `xxd_notify.py send` takes.
# Exit 0 = delivered (stdout is Bark's JSON with "code":200) or skipped as a duplicate.
dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
py=$(command -v python3 || true)
if [ -z "$py" ]; then echo "xxd-notify needs Python 3" >&2; exit 2; fi
exec "$py" "$dir/xxd_notify.py" send "$@"
