# Deployment Configuration

This directory contains deployment-specific configuration files and secrets.

## Structure

```
deploy/
├── config.json          # Bot configuration (gitignored)
└── certs/               # SSL certificates for MikroTik devices (gitignored)
    ├── main_router.crt
    └── office.crt
```

## Setup

1. **Create your config.json**:
   ```bash
   cp config.example.json deploy/config.json
   # Edit deploy/config.json with your settings
   ```

2. **Add your MikroTik SSL certificates**:
   ```bash
   cp /path/to/your/certs/*.crt deploy/certs/
   ```

   In `config.json`, reference certs by filename only:
   ```json
   {
     "name": "Main Router",
     "ssl_cert": "main_router.crt"
   }
   ```

   Or omit `ssl_cert` entirely - it auto-detects based on device name (e.g., "Main Router" → `main_router.crt`)

3. **For Kubernetes deployments**:
   - Create `k8s/secret.yaml` from `k8s/secret.example.yaml`
   - The deploy script will automatically sync these files

## Security

- All files in this directory are gitignored (except this README)
- Never commit sensitive data (passwords, tokens, certificates)
- Keep backups of your config and certificates in a secure location

## Used By

- **docker-compose**: Mounts `deploy/` directly into containers
- **Kubernetes**: `k8s/sync-configs.sh` copies files from here to `k8s/` for deployment
