# How to Add New Commands - The EASY Way! 🚀


## TL;DR

Adding a new command is now **simple**:

### Simple Read Command:
1. Add API method to `client.py`
2. Add formatter to `formatters.py`
3. Add **ONE LINE** to `command_registry.py`

### Sensitive Action:
1. Add API method to `client.py`
2. Add confirmation formatter to `formatters.py`
3. Add **ONE OBJECT** to `command_registry.py`

**That's it!** Everything else is auto-generated!

---

## Example 1: Adding `/firewall` (Simple Read Command)

### Step 1: Add API method to `client.py`

```python
def get_firewall_rules(self) -> list[dict]:
    """Get firewall filter rules."""
    with self.connect() as api:
        firewall = api.get_resource('/ip/firewall/filter')
        return firewall.get()
```

### Step 2: Add formatter to `formatters.py`

```python
def format_firewall_message(identity: str, rules: list[dict]) -> str:
    """Format firewall rules message."""
    if not rules:
        return f"*{identity}*\n\nNo firewall rules found."

    lines = [f"*{identity}* - Firewall Rules\n"]
    for rule in rules:
        chain = rule.get('chain', '?')
        action = rule.get('action', '?')
        lines.append(f"• *{chain}*: {action}")

    return "\n".join(lines)
```

### Step 3: Add to `command_registry.py`

Add this **ONE BLOCK** to the `SIMPLE_COMMANDS` list:

```python
SIMPLE_COMMANDS = [
    SimpleCommand(
        name="status",
        description="System resource status",
        client_method="get_system_resource",
        formatter="format_status_message"
    ),
    # ... existing commands ...

    # ADD THIS:
    SimpleCommand(
        name="firewall",
        description="Firewall filter rules",
        client_method="get_firewall_rules",
        formatter="format_firewall_message"
    ),
]
```

**DONE!** You now have:
- ✅ `/firewall` command
- ✅ Device selection UI
- ✅ Error handling
- ✅ Loading indicators
- ✅ Automatic registration

---

## Example 2: Adding `/backup` (Sensitive Command with MFA)

### Step 1: Add API method to `client.py`

```python
def create_backup(self) -> None:
    """Create system backup."""
    with self.connect() as api:
        system = api.get_resource('/system/backup')
        system.call('save', {'name': 'auto-backup'})
```

### Step 2: Add confirmation formatter to `formatters.py`

```python
def format_backup_confirmation_message(device_name: str) -> str:
    """Format backup confirmation message."""
    return (
        f"⚠️ *Create Backup on {device_name}?*\n\n"
        "This will create a full system backup.\n\n"
        "Are you sure?"
    )
```

### Step 3: Add to `command_registry.py`

Add this to the `SENSITIVE_COMMANDS` list:

```python
SENSITIVE_COMMANDS = [
    SensitiveCommand(
        name="reboot",
        description="Reboot the router",
        client_method="reboot",
        confirmation_formatter="format_reboot_confirmation_message",
        success_message="✅ Reboot command sent to *{device_name}*"
    ),
    # ... existing commands ...

    # ADD THIS:
    SensitiveCommand(
        name="backup",
        description="Create system backup",
        client_method="create_backup",
        confirmation_formatter="format_backup_confirmation_message",
        success_message="✅ Backup created on *{device_name}*",
        help_emoji="🔐"  # Optional
    ),
]
```

**DONE!** You now have:
- ✅ `/backup` command with MFA protection
- ✅ Device selection UI
- ✅ Confirmation dialog with Yes/No buttons
- ✅ MFA recheck at execution (if session expired)
- ✅ Error handling
- ✅ Success message
- ✅ Automatic registration
- ✅ Auto-added to help text


---

## What Gets Auto-Generated?

When you add a command to `command_registry.py`, the system automatically creates:

### For SimpleCommand:
- Command handler (`/command`)
- Callback handler (device selection)
- Device selection keyboard
- Error handling
- Loading indicators
- Registration with bot
- Help text entry

### For SensitiveCommand:
- Command handler with `@requires_mfa`
- Device selection callback
- Confirmation dialog callback
- Execution callback with MFA recheck
- Cancel callback
- Yes/No confirmation keyboard
- Error handling
- Success/failure messages
- Registration with bot
- Help text entry with 🔐 emoji
- Auto-update of `SENSITIVE_ACTIONS`

---

## When to Use Custom Handlers?

You should only create custom handlers in `commands.py` / `callbacks.py` for:

1. **Conditional UI**: Different buttons/keyboards based on data
   - Example: `/updates` shows "Install" button only if update available

2. **Multi-step workflows**: Commands requiring state management
   - Example: Configuration wizard with multiple steps

3. **Complex business logic**: Non-standard command flow
   - Example: Batch operations on multiple devices

**Rule of thumb:** If your command just shows data or performs an action, use the registry!

---

## Advanced: Custom Parameters

Both command classes support additional parameters:

### SimpleCommand:
```python
SimpleCommand(
    name="my_command",
    description="My awesome command",
    client_method="get_something",
    formatter="format_something_message",
    help_emoji="🔥"  # Optional: adds emoji to help text
)
```

### SensitiveCommand:
```python
SensitiveCommand(
    name="my_action",
    description="Do something dangerous",
    client_method="do_something",
    confirmation_formatter="format_my_confirmation_message",
    success_message="✅ Done on *{device_name}*!",
    help_emoji="⚠️"  # Defaults to 🔐
)
```