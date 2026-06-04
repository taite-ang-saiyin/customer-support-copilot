# CloudDesk Enterprise SLA Policy

## Overview

CloudDesk support levels define response targets and escalation handling for Free, Pro, Business, and Enterprise customers. Response targets are not guaranteed resolution times.

## Support Levels

Free plan customers receive community and email support with best-effort response.

Pro plan customers receive standard email support during regional business hours.

Business plan customers receive priority email and live chat support during business hours.

Enterprise plan customers receive priority support, named escalation paths, SSO assistance, and outage handling according to the contract.

## Response Time Targets

Typical first response targets:

| Plan | Low | Medium | High | Urgent |
| --- | --- | --- | --- | --- |
| Free | 3 business days | 2 business days | Best effort | Not available |
| Pro | 1 business day | 8 business hours | 4 business hours | Best effort |
| Business | 8 business hours | 4 business hours | 2 business hours | 1 business hour |
| Enterprise | 4 business hours | 2 business hours | 1 business hour | 30 minutes |

Enterprise contracts may define stricter targets. Always check the account support profile.

## Priority Definitions

Low priority means a question, cosmetic issue, or minor inconvenience with a workaround.

Medium priority means a feature is degraded for one or several users, but core support workflows continue.

High priority means a major feature is unavailable or a large group of users is blocked from normal work.

Urgent priority means a production-impacting issue prevents ticket intake, live chat, customer replies, SSO access for all users, or other business-critical support operations.

## Production-Impacting Issues

Production-impacting issues include:

- New support tickets are not created from email or API.
- Agents cannot access the shared inbox.
- Live chat widget fails for end customers.
- SSO outage blocks all Enterprise agents.
- Automation rules send incorrect replies at scale.
- Analytics slowness alone is usually High, not Urgent, unless it blocks contractual reporting during an active incident.

## Outage Handling

When an outage is suspected, agents should check the internal incident board and known issues list. If multiple customers report the same failure within 15 minutes, escalate to Incident Command.

Use incident tag `CD-INCIDENT-SUSPECTED`. Provide affected features, timestamps, plan level, region, error codes, and customer impact.

## Enterprise Escalation

Enterprise issues should be escalated when:

- The issue is High or Urgent.
- The Designated Support Contact requests escalation.
- SSO, SCIM, API limits, or enterprise integrations are affected.
- The customer references contract terms or service credits.

Escalation route: Enterprise Support Lead, Customer Success Manager, then Incident Command if production impact is confirmed.

## VIP Customer Handling

VIP customers are marked in the support profile with flag `VIP-SUPPORT`. Agents should acknowledge the business impact, keep updates concise, and provide status updates at the interval listed in the account profile.

VIP handling does not bypass security verification, refund approval, or privacy controls.

## Service Credits

Do not promise service credits. Enterprise service credit requests must be reviewed against the signed agreement and official uptime records.
