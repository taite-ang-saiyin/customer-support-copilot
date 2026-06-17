---
title: Known Issues
category: Product Updates
access_level: public
source_type: help_article
summary: Review active and recently resolved CloudDesk issues, workarounds, and when to contact support.
---

# Known Issues

## Delayed Email Notifications

Status: investigating

Some users may receive ticket assignment and mention notifications 10 to 25 minutes late. Ticket creation and agent replies are not delayed.

Workaround: Use the in-app notification center or team inbox filters until the delay is resolved.

Contact support if delayed notifications affect contractual response targets.

## SSO Login Intermittent Failure

Status: monitoring

Some Enterprise users may see intermittent SSO login failures after identity provider redirects. Error codes can include `CD-SSO-403` and `CD-SSO-TIMEOUT`.

Refreshing the login page often succeeds on the second attempt.

Workaround: Ask admins to confirm SAML certificate validity and group mappings. If settings are correct, retry after 2 minutes.

Contact support if all users in a workspace are blocked or if the issue occurs during an active outage window.

## Analytics Dashboard Slow Loading

Status: investigating

Business and Enterprise workspaces with more than 500,000 tickets may see analytics dashboards load in 20 to 60 seconds.

Workaround: Narrow the date range to 30 days, filter by team, or export reports during off-peak hours.

Contact support if dashboards fail with `CD-ANALYTICS-504` or scheduled reports do not send.

## Live Chat Widget Theme Not Saving

Status: resolved

Changes to widget color and welcome text did not save for some Pro workspaces. Engineering cleared the affected cache and deployed validation update `web-widget-2.18.4`.

## Invoice PDF Export Error

Status: resolved

Some invoice PDFs failed to generate after tax ID updates. Billing Engineering regenerated affected invoices.

If you still cannot download an invoice, contact support with the invoice number and browser details.

## Automation Rule Delay

Status: resolved

Automation rules were delayed by up to 8 minutes for high-volume workspaces. No ticket data was lost.

Queue workers were scaled and backlog monitoring was adjusted.
