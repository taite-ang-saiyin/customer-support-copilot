---
title: Login Troubleshooting
category: Account Access
access_level: public
source_type: help_article
summary: Resolve common CloudDesk login issues, including password errors, locked accounts, MFA problems, SSO failures, and browser issues.
---

# Login Troubleshooting

## Incorrect Password

Error `CD-AUTH-401` means the email and password combination was not accepted.

Confirm that you are using the correct CloudDesk login email. If needed, use password reset and check spam or security filtering if the reset email does not arrive.

CloudDesk Support cannot set or disclose passwords.

## Account Locked

Error `CD-AUTH-LOCKED` means the account was locked after repeated failed login attempts or suspicious activity.

Standard lockouts expire after 30 minutes. Support can confirm lockout status, but cannot bypass security controls.

## Two-Factor Authentication Issues

If you lost access to an authenticator app, backup codes, or SMS device, first check whether you still have a recovery code or an active signed-in CloudDesk session.

Workspace members can ask a Workspace Admin to reset MFA from `Settings > Team > Security`.

Workspace Owners may need to complete account recovery verification.

## SSO Login Failure

Error `CD-SSO-403` usually means the identity provider authenticated the user but CloudDesk denied access.

Common causes include missing group mapping, a disabled SSO domain, an expired SAML certificate, or the user not being assigned to the CloudDesk app.

When contacting support about SSO, provide:

- Workspace URL.
- User email.
- Identity provider name, such as Okta, Azure AD, or Google Workspace.
- Approximate timestamp and timezone.
- SAML request ID if available.
- Screenshot of the CloudDesk error code.

## Browser And Cache Issues

Login loops or blank screens may be caused by stale cookies, blocked third-party storage, browser extensions, or old cached scripts.

Try:

- A private browser window.
- Clearing CloudDesk cookies and cache.
- Disabling browser extensions temporarily.
- Updating the browser.
- Trying another supported browser.

## Information To Include When Contacting Support

Please include:

- Login email.
- Workspace URL.
- Error code, such as `CD-AUTH-401`, `CD-AUTH-LOCKED`, or `CD-SSO-403`.
- Timestamp and timezone.
- Browser and operating system.
- Whether the issue affects one user or multiple users.

Do not send passwords, MFA codes, full session cookies, or identity provider secrets.
