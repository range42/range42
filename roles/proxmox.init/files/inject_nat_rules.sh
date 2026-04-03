#!/bin/bash
# inject NAT post-up/post-down rules into a bridge block in /etc/network/interfaces
# usage: inject_nat_rules.sh <bridge_name> <rules_file>
# idempotent: does nothing if MASQUERADE already present

BRIDGE="$1"
RULES_FILE="$2"
INTERFACES="/etc/network/interfaces"

if [ -z "$BRIDGE" ] || [ -z "$RULES_FILE" ]; then
    echo "usage: $0 <bridge_name> <rules_file>"
    exit 1
fi

if [ ! -f "$RULES_FILE" ]; then
    echo "rules file not found: $RULES_FILE"
    exit 1
fi

# check if this specific bridge already has MASQUERADE rules
if awk -v bridge="$BRIDGE" '/iface /{b=($2==bridge)} b&&/MASQUERADE/{found=1} END{exit !found}' "$INTERFACES" 2>/dev/null; then
    echo "NAT rules already present for $BRIDGE — skipping"
    exit 0
fi

# find the bridge-fd line inside the target bridge block and insert rules after it
awk -v bridge="$BRIDGE" -v rules_file="$RULES_FILE" '
    /iface / { in_block = ($2 == bridge) }
    { print }
    in_block && /bridge-fd/ {
        while ((getline line < rules_file) > 0) print line
        close(rules_file)
        in_block = 0
    }
' "$INTERFACES" > "${INTERFACES}.tmp" && mv "${INTERFACES}.tmp" "$INTERFACES"

rm -f "$RULES_FILE"
echo "NAT rules injected into $BRIDGE block"
