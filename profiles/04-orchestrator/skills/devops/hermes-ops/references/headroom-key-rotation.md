# Headroom Proxy — Key Rotation Reference

**Context:** SoloCorp OS runs Headroom proxy as a systemd user service between Hermes and opencode-zen (deepseek-v4-flash-free). Four API keys in circular rotation to survive rate limits.

## File Layout

```
~/.config/headroom/
├── keys.list              # 4 API keys (source of truth)
├── current_key_index      # integer 0-3 (which key is active)
└── .. (no other files)

~/.local/bin/
└── headroom-rotate-key.sh # rotation script

~/.config/systemd/user/
└── headroom-proxy.service # systemd unit

~/.hermes/
└── .env                   # OPENCODE_ZEN_API_KEY (runtime env var)
```

## keys.list Template

```bash
# API Keys for opencode-zen (deepseek-v4-flash-free)
# 4 keys circular rotation — when one hits rate limit, swap to next
OPENCODE_ZEN_KEY_1="sk-..."
OPENCODE_ZEN_KEY_2="sk-..."
OPENCODE_ZEN_KEY_3="sk-..."
OPENCODE_ZEN_KEY_4="sk-..."
```

## Rotation Script Structure

```bash
#!/bin/bash
# headroom-rotate-key.sh — rotate API key to next in pool
set -euo pipefail

CONFIG_DIR="$HOME/.config/headroom"
KEYS_FILE="$CONFIG_DIR/keys.list"
HERMES_ENV="$HOME/.hermes/.env"
CURRENT_INDEX_FILE="$CONFIG_DIR/current_key_index"

# Load keys
source "$KEYS_FILE"

KEYS=("$OPENCODE_ZEN_KEY_1" "$OPENCODE_ZEN_KEY_2" "$OPENCODE_ZEN_KEY_3" "$OPENCODE_ZEN_KEY_4")
TOTAL_KEYS=${#KEYS[@]}

# Read current index (default 0)
CURRENT_INDEX=$(cat "$CURRENT_INDEX_FILE" 2>/dev/null || echo 0)

# Advance circularly
NEXT_INDEX=$(( (CURRENT_INDEX + 1) % TOTAL_KEYS ))
NEW_KEY="${KEYS[$NEXT_INDEX]}"

# Validate not empty
if [[ -z "$NEW_KEY" ]]; then
    echo "ERROR: Key #$((NEXT_INDEX + 1)) is empty!" >&2
    exit 1
fi

# Save index
echo "$NEXT_INDEX" > "$CURRENT_INDEX_FILE"

# Update .env
sed -i "s|^OPENCODE_ZEN_API_KEY=.*|OPENCODE_ZEN_API_KEY=$NEW_KEY|" "$HERMES_ENV"

# Restart proxy
systemctl --user restart headroom-proxy
echo "Rotated to key #$((NEXT_INDEX + 1))"
```

## systemd Unit Template

```ini
[Unit]
Description=Headroom Optimization Proxy for opencode-zen
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/headroom-proxy-start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

## Verification Commands

```bash
# Check current active key index
cat ~/.config/headroom/current_key_index

# Test rotation
~/.local/bin/headroom-rotate-key.sh force-rotate

# Verify proxy health after rotation
curl -s http://127.0.0.1:8787/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['status'], '| backend:', d['config']['backend'])"
```

## History

| Date | Change |
|------|--------|
| 2026-06-15 | Created with 4 keys. Previous version used nohup + 3 keys. Rotate script updated to support KEY_4. Proxy was initially running wrong backend (Anthropic) — fixed to anyllm + opencode-zen. |
