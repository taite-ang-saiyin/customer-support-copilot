---
title: Enterprise Support And Response Targets
category: Support
access_level: public
source_type: help_article
summary: Understand CloudDesk support levels, response targets, priority definitions, outage handling, and Enterprise escalation.
---

# Enterprise Support And Response Targets

## Support Levels

CloudDesk support levels define response targets and escalation handling for Free, Pro, Business, and Enterprise customers.

Response targets are not guaranteed resolution times.

Free plan customers receive community and email support with best-effort response.

Pro plan customers receive standard email support during regional business hours.

Business plan customers receive priority email and live chat support during business hours.

Enterprise plan customers receive priority support, named escalation paths, SSO assistance, and outage handling according to the contract.

## Typical First Response Targets

| Plan | Low | Medium | High | Urgent |
| --- | --- | --- | --- | --- |
| Free | 3 business days | 2 business days | Best effort | Not available |
| Pro | 1 business day | 8 business hours | 4 business hours | Best effort |
| Business | 8 business hours | 4 business hours | 2 business hours | 1 business hour |
| Enterprise | 4 business hours | 2 business hours | 1 business hour | 30 minutes |

Enterprise contracts may define stricter targets. Check your account support profile for contract-specific details.

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

Analytics slowness alone is usually High, not Urgent, unless it blocks contractual reporting during an active incident.

## Outage Handling

When an outage is suspected, CloudDesk checks active incidents and known issues.

If multiple customers report the same failure within a short period, CloudDesk escalates to incident handling.

When contacting support, provide affected features, timestamps, plan level, region, error codes, and customer impact.

## Enterprise Escalation

Enterprise issues may be escalated when:

- The issue is High or Urgent.
- The Designated Support Contact requests escalation.
- SSO, SCIM, API limits, or enterprise integrations are affected.
- The customer references contract terms or service credits.

## Service Credits

Do not assume service credits are automatically available. Enterprise service credit requests are reviewed against the signed agreement and official uptime records.
