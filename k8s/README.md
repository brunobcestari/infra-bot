# Kubernetes Deployment Guide

Deploy the Telegram Infrastructure Bot to your Kubernetes Cluster.
Tested with k3s cluster running on Raspberry Pi.

## Overview

The bot is deployed using:
- **Container Registry**: GitHub Container Registry (ghcr.io)
- **Multi-arch Support**: Built for both amd64 and arm64 (Raspberry Pi)
- **Storage**: NFS-based persistent storage for MFA database (update the pvc.yaml file)
- **Security**: All sensitive data passed via Secrets and ConfigMaps


## Configuration Steps

### 1. Create and Configure Secrets

First, create your secret file from the example:

```bash
cp k8s/secret.example.yaml k8s/secret.yaml
```

Then edit `k8s/secret.yaml` and replace all placeholder values:

```yaml
stringData:
  TELEGRAM_BOT_TOKEN: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # From @BotFather
  MIKROTIK_MAIN_ROUTER_PASSWORD: "your-actual-password"
  MFA_ENCRYPTION_KEY: "generated-key-here"
```

Generate the MFA encryption key:
```bash
openssl rand -base64 32
```

Add passwords for each MikroTik device in your config.json:
```yaml
MIKROTIK_<DEVICE_SLUG>_PASSWORD: "password"
```

The slug is derived from the device name (e.g., "Main Router" → `MAIN_ROUTER`).

### 2. Verify config.json

Ensure your `config.json` in the project root contains:
- Your Telegram user ID in `admin_ids`
- Correct MikroTik device configurations (host, port, username)
- MFA settings (note: `db_path` should be `/data/mfa.db`)

Example:
```json
{
  "telegram": {
    "admin_ids": [YOUR_TELEGRAM_ID]
  },
  "mfa": {
    "enabled": true,
    "session_duration_minutes": 15,
    "db_path": "/data/mfa.db"
  },
  "devices": {
    "mikrotik": [
      {
        "name": "Main Router",
        "host": "192.168.88.1",
        "port": 8729,
        "username": "telegram-bot",
        "ssl_cert": "mikrotik/certs/main_router.crt"
      }
    ]
  }
}
```

### 3. Add SSL Certificates

Place your MikroTik SSL certificates in `app/mikrotik/certs/`.

If you have multiple devices, update `kustomization.yaml`:
```yaml
configMapGenerator:
  - name: infra-bot-certs
    files:
      - ../app/mikrotik/certs/main_router.crt
      - ../app/mikrotik/certs/office.crt  # Add more as needed
```

## Deploy to Kubernetes

1. **Apply the configuration**:
   ```bash
   kubectl apply -k k8s/
   ```

2. **Verify deployment**:
   ```bash
   # Check pods
   kubectl get pods -n infra-bot

   # Check if PVC is bound
   kubectl get pvc -n infra-bot

   # View logs
   kubectl logs -n infra-bot -l app=infra-bot -f
   ```

3. **Check the pod is running**:
   ```bash
   kubectl get pods -n infra-bot
   ```

   You should see:
   ```
   NAME                         READY   STATUS    RESTARTS   AGE
   infra-bot-xxxxxxxxxx-xxxxx   1/1     Running   0          30s
   ```

## Updating

### Update Configuration

After changing `config.json` or certificates:

```bash
# Reapply configuration
kubectl apply -k k8s/

# Restart to pick up new config
kubectl rollout restart deployment/infra-bot -n infra-bot
```

### Update Bot Code

To get a new release, just restart the deployment:

```bash
kubectl rollout restart deployment/infra-bot -n infra-bot
```

Or tag a release for versioned deployments:

```bash
git tag v1.0.1
git push origin v1.0.1
```

Then update the image tag in `deployment.yaml`:
```yaml
image: ghcr.io/brunobcestari/infra-bot:v1.0.1
```

### Update Secrets

To update secrets:

```bash
kubectl edit secret infra-bot-secrets -n infra-bot
```

Or delete and recreate:
```bash
kubectl delete secret infra-bot-secrets -n infra-bot
kubectl apply -f k8s/secret.yaml
kubectl rollout restart deployment/infra-bot -n infra-bot
```

## Troubleshooting

### Pod won't start

Check events and logs:
```bash
kubectl describe pod -n infra-bot -l app=infra-bot
kubectl logs -n infra-bot -l app=infra-bot --previous
```


### Storage issues

Check PVC status:
```bash
kubectl get pvc -n infra-bot
kubectl describe pvc infra-bot-data -n infra-bot
```

Ensure your NFS storage class is working:
```bash
kubectl get storageclass
```

### Verify mounted files

```bash
# Check config.json
kubectl exec -n infra-bot deployment/infra-bot -- cat /app/config.json

# Check certificates
kubectl exec -n infra-bot deployment/infra-bot -- ls -la /app/mikrotik/certs/

# Check data directory
kubectl exec -n infra-bot deployment/infra-bot -- ls -la /data/
```

## Backup MFA Database

The MFA database contains user TOTP secrets. Back it up regularly:

```bash
kubectl exec -n infra-bot deployment/infra-bot -- cat /data/mfa.db > mfa-backup-$(date +%Y%m%d).db
```

## Uninstall

To completely remove the bot:

```bash
kubectl delete -k k8s/
```

**Warning**: This deletes the PVC and MFA database. Backup first if needed!

## Security Notes

- Keep `MFA_ENCRYPTION_KEY` backed up securely
- Consider using Sealed Secrets or External Secrets Operator for production
