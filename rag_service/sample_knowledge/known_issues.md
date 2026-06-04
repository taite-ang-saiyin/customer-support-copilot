# CloudDesk Known Issues

## Overview

This document lists synthetic active and recently resolved CloudDesk issues for support demo scenarios. Use it to identify customer impact, workarounds, and escalation paths.

## Active Issue: Delayed Email Notifications

Status: investigating  
Issue ID: `CD-KI-2026-014`  
Affected feature: Email notifications for ticket assignment and mentions  
First observed: 2026-05-28 09:20 UTC

Some users may receive ticket assignment and mention notifications 10 to 25 minutes late. Ticket creation and agent replies are not delayed.

Workaround: Ask agents to use the in-app notification center or team inbox filters until the delay is resolved.

Escalate if an Enterprise customer reports missed contractual response targets because of delayed notifications.

## Active Issue: SSO Login Intermittent Failure

Status: monitoring  
Issue ID: `CD-KI-2026-018`  
Affected feature: SAML SSO login  
Error codes: `CD-SSO-403`, `CD-SSO-TIMEOUT`  
First observed: 2026-05-30 14:05 UTC

Some Enterprise users may see intermittent SSO login failures after identity provider redirects. Refreshing the login page often succeeds on the second attempt.

Workaround: Ask admins to confirm SAML certificate validity and group mappings. If settings are correct, advise affected users to retry after 2 minutes.

Escalate if all users in a workspace are blocked or if the customer is in an active outage window.

## Active Issue: Analytics Dashboard Slow Loading

Status: investigating  
Issue ID: `CD-KI-2026-021`  
Affected feature: Analytics dashboard and scheduled report preview  
First observed: 2026-05-31 07:45 UTC

Business and Enterprise workspaces with more than 500,000 tickets may see analytics dashboards load in 20 to 60 seconds.

Workaround: Narrow the date range to 30 days, filter by team, or export reports during off-peak hours.

Escalate if dashboards fail with `CD-ANALYTICS-504` or if scheduled reports do not send.

## Recently Resolved: Live Chat Widget Theme Not Saving

Status: resolved  
Issue ID: `CD-KI-2026-009`  
Affected feature: Live chat widget appearance settings  
Resolved: 2026-05-22 18:10 UTC

Changes to widget color and welcome text did not save for some Pro workspaces. The issue was caused by a configuration cache mismatch.

Resolution: Engineering cleared the affected cache and deployed validation update `web-widget-2.18.4`.

## Recently Resolved: Invoice PDF Export Error

Status: resolved  
Issue ID: `CD-KI-2026-011`  
Affected feature: Billing invoice PDF download  
Error code: `CD-INV-EXPORT-500`  
Resolved: 2026-05-25 11:30 UTC

Some invoice PDFs failed to generate after tax ID updates. Billing Engineering regenerated affected invoices.

Support action: If a customer still cannot download an invoice, collect invoice number and browser details, then escalate as a new case.

## Recently Resolved: Automation Rule Delay

Status: resolved  
Issue ID: `CD-KI-2026-012`  
Affected feature: Automation rules for ticket tags and routing  
Resolved: 2026-05-26 16:40 UTC

Automation rules were delayed by up to 8 minutes for high-volume workspaces. No ticket data was lost.

Resolution: Queue workers were scaled and backlog monitoring was adjusted.
