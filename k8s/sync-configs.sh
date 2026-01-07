#!/bin/bash
# Sync config and certs from deploy/ to k8s/ directory for deployment

set -e

echo "📋 Syncing configuration files from deploy/..."

# Copy config.json
cp ../deploy/config.json ./config.json
echo "✅ Copied config.json"

# Copy certificates
mkdir -p ./certs
cp ../deploy/certs/*.crt ./certs/ 2>/dev/null || echo "⚠️  No certificates found"
echo "✅ Copied certificates"

echo "✨ Config sync complete!"
