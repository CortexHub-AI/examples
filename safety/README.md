## Safety Policies Example

This example shows how CortexHub policies control sensitive tool calls such as
destructive actions, privileged commands, and external network access.

### Prerequisites
- CortexHub API key
- A project with the **Production Safety** policy pack installed

### Run
```bash
export CORTEXHUB_DESTRUCTIVE_TOOLS="rm,delete_file,sudo"
export CORTEXHUB_EXTERNAL_NETWORK_TOOLS="curl,wget"
uv run python safety/main.py
```

### What to expect
Depending on your policies:
- Destructive tools may require approval
- External network tools may be blocked
- You’ll see clear allow/deny output in the console
