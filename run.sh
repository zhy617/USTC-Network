#!/usr/bin/env sh
set -eu

CONFIG=""
DEBUG=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --debug)
            DEBUG=1
            shift
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        *)
            echo "Usage: ./run.sh [--debug] [--config FILE]"
            exit 2
            ;;
    esac
done

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed."
    echo "Install it with:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

if [ -z "$CONFIG" ]; then
    if [ -f "ustc-network.local.conf" ]; then
        CONFIG="ustc-network.local.conf"
    else
        CONFIG="ustc-network.conf"
    fi
fi

if [ "$DEBUG" -eq 1 ]; then
    exec uv run python UstcNetwork.py --debug-login "$CONFIG"
else
    exec uv run python UstcNetwork.py "$CONFIG"
fi
