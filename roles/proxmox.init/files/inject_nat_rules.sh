#!/bin/bash
# manage NAT post-up/post-down rules in a bridge block in /etc/network/interfaces
#
# usage: inject_nat_rules.sh <bridge_name> <rules_file|REMOVE>
#   rules_file = inject these rules (replaces any existing MASQUERADE for this bridge)
#   REMOVE     = remove MASQUERADE rules for this bridge
#
# always overwrites — no skip logic. reflects the desired state.

BRIDGE="$1"
RULES_FILE="$2"
INTERFACES="/etc/network/interfaces"

if [ -z "$BRIDGE" ] || [ -z "$RULES_FILE" ]; then
    echo "usage: $0 <bridge_name> <rules_file|REMOVE>"
    exit 1
fi

# step 1: remove any existing MASQUERADE lines for this bridge
awk -v bridge="$BRIDGE" '
    /iface / { in_block = ($2 == bridge) }
    in_block && /MASQUERADE/ { next }
    { print }
' "$INTERFACES" > "${INTERFACES}.tmp" && mv "${INTERFACES}.tmp" "$INTERFACES"

# step 2: if rules_file is "REMOVE", we're done (just cleaned up)
if [ "$RULES_FILE" = "REMOVE" ]; then
    echo "NAT rules removed for $BRIDGE"
    exit 0
fi

# step 3: inject new rules after bridge-fd
if [ ! -f "$RULES_FILE" ]; then
    echo "rules file not found: $RULES_FILE"
    exit 1
fi

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
echo "NAT rules updated for $BRIDGE"
