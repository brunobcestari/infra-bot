# Infrastructure Bot

A Telegram bot for managing network infrastructure. Currently supports MikroTik RouterOS devices.

## Features

- **Multi-device support** - Manage multiple routers from one bot
- **System monitoring** - CPU, memory, disk, uptime
- **Network info** - Interfaces, DHCP leases, logs
- **Maintenance** - Check/install updates, reboot
- **Secure** - Admin-only access, SSL/TLS connections, MFA for critical operations

## Setup

### 1. Install dependencies

```bash
poetry install
```

### 2. Create deployment configuration

Create your deployment config from the example:

```bash
cp config.example.json deploy/config.json
cp .env.example .env
```

Create the certs directory:

```bash
mkdir -p deploy/certs
```

You'll add MikroTik SSL certificates here in step 5.

### 3. Configure your devices

Edit `deploy/config.json`:

```json
{
  "telegram": {
    "admin_ids": [YOUR_TELEGRAM_USER_ID]
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
        "ssl_cert": "api-cert.crt"
      }
    ]
  }
}
```

### 4. Add secrets to `.env`

```bash
TELEGRAM_BOT_TOKEN="your-bot-token"
MIKROTIK_MAIN_ROUTER_PASSWORD="your-password"
MFA_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

### 5. Create and configure SSL certificate on MikroTik

The bot connects to MikroTik using the API-SSL service (port 8729 by default), which requires a certificate.

#### Create a self-signed certificate

```routeros
# Create a self-signed certificate (valid for 10 years)
/certificate add name=api-cert common-name=router.local key-size=2048 \
    days-valid=3650 key-usage=digital-signature,key-encipherment \
    subject-alt-name=IP:192.168.88.1

# Sign the certificate
/certificate sign api-cert

# Wait a few seconds for signing to complete, then verify
/certificate print
```

#### Enable API-SSL and assign the certificate

```routeros
# Enable API-SSL service
/ip service set api-ssl disabled=no

# Set the certificate for API-SSL (use the certificate name from above)
/ip service set api-ssl certificate=api-cert

# Optionally restrict API-SSL to specific IPs
/ip service set api-ssl address=192.168.88.0/24
```

#### Export the certificate for the bot

```routeros
# Export only the public certificate (.crt file)
/certificate export-certificate api-cert file-name=api-cert
```

Use SFTP/SCP to download the `.crt` file from MikroTik's `/` directory, then copy it to `deploy/certs/` on your bot server.

### 6. Create MikroTik API user

Create a dedicated user with minimal required permissions:

```routeros
# Create a restricted user group for the bot
/user group add name=telegram-api \
    policy=read,write,api,rest-api,!ftp,!ssh,!telnet,!policy,!password,!sensitive

# Create the bot user
/user add name=telegram-bot group=telegram-api password=your-strong-password
```

**Required permissions explained:**
- `read` - Read configuration and status
- `write` - Execute commands (reboot, upgrade)
- `api` - Access the API service
- `rest-api` - REST API access
- `!ftp,!ssh,!telnet` - Deny interactive access
- `!policy` - Prevent modifying user policies
- `!password` - Prevent changing passwords
- `!sensitive` - Hide sensitive data

### 7. Enroll users in MFA

```bash
# Enroll a user by Telegram ID
poetry run python scripts/manage_mfa.py enroll YOUR_TELEGRAM_USER_ID

# Or with Docker
docker-compose exec telegram_bot python scripts/manage_mfa.py enroll YOUR_TELEGRAM_USER_ID
```

Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.).

## Run

```bash
# Direct
poetry run python -m app.main

# Docker
docker compose up --build
```

## Commands

| Command | Description |
|---------|-------------|
| `/status` | System resources |
| `/interfaces` | Network interfaces |
| `/leases` | DHCP leases |
| `/logs` | Recent logs |
| `/updates` | Check for updates |
| `/upgrade` | Install updates (requires MFA) |
| `/reboot` | Reboot device (requires MFA) |
| `/mfa_auth` | Authenticate and create/refresh MFA session |
| `/mfa_status` | Check MFA enrollment status |

## Tests

```bash
poetry run pytest
poetry run pytest --cov=app
```

## License

GPL-3.0

## Deployment

### Production (Recommended)

Both deployment methods use the same container image from GitHub Container Registry and pull configuration from `deploy/`.

#### Option 1: Docker Compose

```bash
# Pull latest image and start
docker compose pull
docker compose up -d

# View logs
docker compose logs -f
```

The bot runs with:
- Host network access (to reach local MikroTik routers)
- Resource limits (512MB RAM, 1.0 CPU)
- Non-root user (UID 1000)
- Auto-restart on failure

#### Option 2: Kubernetes

See detailed instructions in [k8s/README.md](k8s/README.md)

```bash
cd k8s
./deploy.sh
```

### Development

For local development with live code changes:

```bash
# Build and run with dev overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Or build locally
docker build -t infra-bot:dev .
docker run --rm -it \
  --network host \
  --env-file .env \
  -v ./deploy/config.json:/app/config.json:ro \
  -v ./deploy/certs:/app/certs:ro \
  -v ./data:/data \
  infra-bot:dev
```

The dev compose file:
- Builds locally instead of pulling from registry
- Mounts source code for live development
- Relaxes resource limits

### Deployment Comparison

| Feature | docker-compose | Kubernetes |
|---------|---------------|------------|
| **Image source** | ghcr.io (production)<br>Local build (dev) | ghcr.io |
| **Config** | `deploy/config.json` | ConfigMap (from `deploy/`) |
| **Secrets** | `.env` file | Kubernetes Secret |
| **Certs** | `deploy/certs/` | ConfigMap (from `deploy/`) |
| **Data** | Local volume (`./data`) | Local NVMe PersistentVolume |
| **Network** | Host network | Host network |
| **Resources** | 512MB / 1.0 CPU | 512MB / 1.0 CPU |
| **User** | 1000:1000 | 1000:1000 |
| **Best for** | Single server, development | Production, HA, scaling |

