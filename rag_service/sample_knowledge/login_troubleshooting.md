# CloudDesk Login Troubleshooting

## Overview

This guide helps agents resolve common CloudDesk login issues, including password errors, locked accounts, two-factor authentication problems, SSO failures, and browser issues.

## Incorrect Password

Customers may see error `CD-AUTH-401` when the email and password combination is incorrect. Ask the customer to confirm they are using the correct CloudDesk login email.

Support action:

- Send the password reset link from the admin console if the user can access their email.
- Ask the customer to check spam or security filtering if the reset email is missing.
- Do not set or disclose passwords for customers.

## Account Locked

Error `CD-AUTH-LOCKED` means the account was locked after repeated failed login attempts or suspicious activity. Standard lockouts expire after 30 minutes.

Agents may confirm the lockout status but must not bypass security controls. If the user is a Workspace Owner and business impact is high, escalate to Security Support with reason `AUTH-LOCKOUT-OWNER`.

## Two-Factor Authentication Issue

Customers may lose access to an authenticator app, backup codes, or SMS device. Ask whether they still have access to a recovery code or a signed-in CloudDesk session.

Support action:

- Direct the customer to use a backup code if available.
- For workspace members, ask a Workspace Admin to reset MFA from `Settings > Team > Security`.
- For Workspace Owners, follow account recovery verification.

Escalate if the customer cannot verify ownership or reports a suspected account takeover.

## SSO Login Failure

Error `CD-SSO-403` usually means the identity provider authenticated the user but CloudDesk denied access. Causes include missing group mapping, disabled SSO domain, expired SAML certificate, or user not assigned to the CloudDesk app.

Required information:

- Workspace URL.
- User email.
- Identity provider name, such as Okta, Azure AD, or Google Workspace.
- Approximate timestamp and timezone.
- SAML request ID if available.
- Screenshot of the CloudDesk error code.

Escalate to Enterprise Support if SSO affects multiple users or an Enterprise admin cannot access the workspace.

## Browser and Cache Issues

Login loops or blank screens may be caused by stale cookies, blocked third-party storage, browser extensions, or old cached scripts.

Ask the customer to try:

- A private browser window.
- Clearing CloudDesk cookies and cache.
- Disabling browser extensions temporarily.
- Updating the browser.
- Trying another supported browser.

If the same error occurs across multiple browsers and networks, gather HAR logs and escalate to Support Engineering.

## Required Information From Customer

Collect:

- Login email.
- Workspace URL.
- Error code, such as `CD-AUTH-401`, `CD-AUTH-LOCKED`, or `CD-SSO-403`.
- Timestamp and timezone.
- Browser and operating system.
- Whether the issue affects one user or multiple users.

Do not ask for passwords, MFA codes, full session cookies, or identity provider secrets.

## When To Escalate

Escalate login issues when:

- Multiple users cannot log in.
- The affected user is the only Workspace Owner.
- SSO fails for an Enterprise workspace.
- The customer reports suspected account compromise.
- Error `CD-AUTH-SUSPICIOUS` appears.
- Standard recovery steps fail after identity verification.
