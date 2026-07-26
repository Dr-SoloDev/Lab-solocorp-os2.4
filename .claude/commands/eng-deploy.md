---
name: eng-deploy
description: 🚀 Deploy — trigger deploy, check status, rollback service
skill: "@solocorp/engineering/deploy"
---

# Deploy

Trigger deployment, check status, or rollback any service in SoloCorp OS.

## Usage
```
/eng-deploy <service> <environment> <action>
```

Actions: `deploy`, `status`, `rollback`
Environments: `dev`, `staging`, `production`

## Example
```
/eng-deploy central-bus staging status
```
