#!/bin/bash
# Sync config and certs to k8s directory for deployment

set -e

echo "📋 Syncing configuration files..."

# Copy config.json
cp ../config.json ./config.json
echo "✅ Copied config.json"

# Copy certificates
mkdir -p ./certs
cp ../app/mikrotik/certs/*.crt ./certs/ 2>/dev/null || echo "⚠️  No certificates found"
echo "✅ Copied certificates"

echo "✨ Config sync complete!"
