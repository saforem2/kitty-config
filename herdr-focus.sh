#!/usr/bin/env bash
# Kitty open-actions wrapper: receives $URL via HERDR_PLUGIN_CLICKED_URL env
HERDR_PLUGIN_CLICKED_URL="$1" python3 ~/.config/herdr/plugins/local/herdr-links/focus.py
