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

### 2. Create config files

Copy the example files:

```bash
cp config.example.json config.json
cp .env.example .env
```

### 3. Configure your devices

Edit `config.json`:

```json
{
  "telegram": {
    "admin_ids": [YOUR_TELEGRAM_USER_ID]
  },
  "mfa": {
    "enabled": true,
    "session_duration_minutes": 15,
    "db_path": "mfa.db"
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

### 4. Add secrets to `.env`

```bash
TELEGRAM_BOT_TOKEN="your-bot-token"
MIKROTIK_MAIN_ROUTER_PASSWORD="your-password"
MFA_ENCRYPTION_KEY="$(openssl rand -base64 32)"
```

### 5. Export SSL certificate from MikroTik

```
/certificate export-certificate [your-api-cert] file-name=api
```

Copy the `.crt` file to `app/mikrotik/certs/`.

### 6. Create MikroTik API user

```
/user group add name=telegram-api policy=read,write,api,rest-api,!ftp,!ssh,!telnet,!policy,!password
/user add name=telegram-bot group=telegram-api password=your-password
```

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
| `/mfa_status` | Check MFA enrollment status |

## Tests

```bash
poetry run pytest
poetry run pytest --cov=app
```

## License

GPL-3.0
