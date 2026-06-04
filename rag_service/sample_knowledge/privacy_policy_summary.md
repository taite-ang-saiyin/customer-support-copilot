# CloudDesk Privacy Policy Summary

## Overview

This summary explains common privacy topics for CloudDesk support conversations. It is not legal advice and does not replace a signed data processing agreement.

## Customer Data CloudDesk Stores

CloudDesk may store workspace configuration, user profile details, support tickets, live chat transcripts, customer contact profiles, automation rules, analytics metadata, audit logs, and integration settings.

Typical user profile fields include name, email address, role, timezone, and authentication settings. Ticket content may include information submitted by the customer's end users.

## Data Retention Summary

Active workspace data is retained while the subscription is active. Deleted tickets are retained in recoverable state for 30 days, then moved to deletion queues.

Audit logs may be retained for up to 1 year for Business plans and up to 7 years for Enterprise plans if contractually required. Backups may take up to 90 days to age out.

## Data Deletion Requests

Workspace Owners can request deletion of a workspace or specific personal data by contacting support from a verified admin email.

Required information:

- Workspace URL.
- Requester email and role.
- Data subject email, if requesting deletion for a specific person.
- Scope of deletion, such as profile, tickets, chat transcripts, or full workspace closure.
- Legal or contractual deadline if applicable.

Escalate deletion requests with code `PRIV-DELETE-REQUEST`. Do not confirm completion until Privacy Operations marks the request complete.

## Export Requests

Admins can export tickets and customer profiles from `Settings > Data > Exports` if exports are enabled for the plan.

If a customer requests a privacy export, collect the workspace URL, requester role, data scope, and preferred format. Export requests for Enterprise customers may require approval from the Designated Support Contact.

## PII Handling

PII means information that can identify a person, such as email address, phone number, name, IP address, or ticket content about a specific individual.

Agents should avoid copying unnecessary PII into internal notes. Use ticket links and record IDs instead of pasting full message content when possible.

Never ask customers to send passwords, full payment card numbers, MFA codes, API secrets, or private keys.

## Security And Privacy Escalation

Escalate to Privacy Operations or Security Support when:

- The customer requests deletion, export, correction, or restriction of personal data.
- The customer mentions GDPR, CCPA, DPA, subpoena, breach, regulator, or legal complaint.
- The request involves audit logs, backups, or Enterprise retention exceptions.
- The requester is not an admin but asks for workspace-wide data.

Use tag `PRIVACY-REVIEW` and include only minimum necessary details.

## What Agents Should Not Disclose

Agents must not disclose:

- Internal infrastructure details.
- Other customers' data.
- Full security investigation notes.
- Employee access logs beyond approved audit exports.
- Whether a specific end user exists in a workspace unless the requester is verified and authorized.

Use approved summaries and escalate when unsure.
