#!/bin/bash
set -e

echo "🚀 Deploying infra-bot to Kubernetes..."

# Check if config.json exists
if [ ! -f "../deploy/config.json" ]; then
    echo "❌ Error: config.json not found in deploy/"
    echo "Please create it: cp config.example.json deploy/config.json"
    exit 1
fi

# Check if secret.yaml exists
if [ ! -f "secret.yaml" ]; then
    echo "❌ Error: secret.yaml not found"
    echo "Please create it from secret.example.yaml and fill in your credentials"
    exit 1
fi

echo "✅ Pre-flight checks passed"

# Sync config files to k8s directory
echo "📋 Syncing configuration files..."
./sync-configs.sh

# Apply Kubernetes resources (kustomize will generate ConfigMaps)
echo "📦 Applying Kubernetes resources..."
kubectl apply -k .

# Wait for deployment
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=120s deployment/infra-bot -n infra-bot

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Check the status with:"
echo "  kubectl get pods -n infra-bot"
echo ""
echo "View logs with:"
echo "  kubectl logs -n infra-bot -l app=infra-bot -f"
