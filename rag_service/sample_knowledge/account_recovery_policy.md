# CloudDesk Account Recovery Policy

## Purpose

This policy explains how support agents handle account recovery while protecting CloudDesk workspaces from unauthorized access.

## Lost Access To Email

If a user lost access to their login email, agents should first ask whether another Workspace Admin can update the user's email address. Admin-assisted recovery is preferred for members and team leads.

If no admin is available, collect the workspace URL, old email, requested new email, role, and reason for lost access. Do not change the email until identity verification is complete.

## Admin Account Recovery

For Workspace Owner or Admin recovery, the requester must prove authority over the workspace. Acceptable verification may include:

- Reply from the verified billing email on file.
- Confirmation from another active Workspace Owner.
- Recent invoice number and billing details.
- Enterprise contract contact confirmation.
- Domain ownership verification using a DNS TXT record.

Agents must document every verification step in the ticket.

## Identity Verification Steps

Minimum verification for self-service account recovery:

1. Confirm workspace URL and login email.
2. Confirm the user's role and last successful login date if available.
3. Confirm billing or admin relationship.
4. Verify access to the company domain or billing contact.
5. Escalate if any answer conflicts with account records.

Verification case type: `SEC-ACCT-RECOVERY`.

## Enterprise Admin Recovery

Enterprise admin recovery must involve the Customer Success Manager or Enterprise Support lead. If the customer has a named Designated Support Contact, use that contact list for validation.

If all admins are locked out because of SSO misconfiguration, escalate with priority High or Urgent depending on production impact. Use escalation reason `ENT-ADMIN-LOCKOUT`.

## Security Restrictions

Agents must not:

- Share account passwords or reset links with third parties.
- Disable MFA without verification.
- Change owner email based only on a forwarded message.
- Reveal workspace member lists to unverified requesters.
- Accept screenshots as the only proof of ownership.
- Ask for government IDs unless Security Team specifically requests it under an approved workflow.

Agents may:

- Send reset instructions to the verified email on file.
- Ask an active admin to complete the change.
- Start a domain verification process.
- Escalate to Security Support for review.

## Escalation To Security Team

Escalate immediately when:

- The requester cannot access the billing email or company domain.
- There is a dispute between former and current employees.
- The customer reports suspected account takeover.
- The request involves deleting audit logs or changing ownership after termination.
- The workspace contains regulated data or has Enterprise security addendum terms.

Use escalation code `CD-SEC-RECOVERY-REVIEW` and include all verification evidence.

## Agent Response Guidance

Use neutral, security-focused language:

"For your protection, we need to verify workspace ownership before changing account access. I can start that process and document the required details."

Do not imply that recovery is guaranteed.
