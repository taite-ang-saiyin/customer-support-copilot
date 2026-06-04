# CloudDesk Past Resolved Tickets

## Ticket CD-TKT-2026-1001

Category: Duplicate charge  
Customer plan: Business  
Issue summary: Customer reported two USD 249 charges on the same card for the May billing period.  
Root cause: Payment gateway retried after a timeout and both attempts settled.  
Resolution: Billing Operations verified duplicate invoice `CD-INV-2026-03881` and refunded the second charge.  
Required information: Workspace URL, billing email, invoice numbers, charge dates, amount, last four card digits.  
Useful knowledge source: `refund_policy.md` duplicate charges section.  
Final outcome: Refund approved and submitted within 2 business days.

## Ticket CD-TKT-2026-1002

Category: Failed payment  
Customer plan: Pro  
Issue summary: Customer could not renew subscription and saw `CD-PAY-402`.  
Root cause: Card issuer declined renewal because the card had expired.  
Resolution: Agent guided Billing Admin to update payment method and retry invoice payment.  
Required information: Workspace URL, billing email, invoice number, payment error code.  
Useful knowledge source: `billing_faq.md` failed payments section.  
Final outcome: Invoice paid and workspace remained active.

## Ticket CD-TKT-2026-1003

Category: Login locked  
Customer plan: Business  
Issue summary: Workspace Owner saw `CD-AUTH-LOCKED` after several failed password attempts.  
Root cause: Security lockout triggered by repeated incorrect password entries.  
Resolution: Agent confirmed lockout duration, sent password reset instructions, and advised waiting 30 minutes.  
Required information: Login email, workspace URL, error code, timestamp, browser.  
Useful knowledge source: `login_troubleshooting.md` account locked section.  
Final outcome: Owner regained access after password reset.

## Ticket CD-TKT-2026-1004

Category: SSO failure  
Customer plan: Enterprise  
Issue summary: Multiple users saw `CD-SSO-403` after Okta login.  
Root cause: Okta group mapping was renamed and no longer matched CloudDesk SSO rules.  
Resolution: Enterprise Support helped admin update group mapping and test SAML login.  
Required information: Workspace URL, affected emails, identity provider, timestamp, SAML request ID.  
Useful knowledge source: `login_troubleshooting.md` SSO login failure section.  
Final outcome: SSO restored for all users.

## Ticket CD-TKT-2026-1005

Category: Refund request  
Customer plan: Pro  
Issue summary: Customer requested refund for unused monthly subscription after renewal.  
Root cause: Renewal completed normally before cancellation request.  
Resolution: Agent explained non-refundable monthly renewal policy and documented customer feedback.  
Required information: Workspace URL, billing email, invoice number, cancellation date.  
Useful knowledge source: `refund_policy.md` non-refundable cases section.  
Final outcome: Refund not approved; customer canceled future renewal.

## Ticket CD-TKT-2026-1006

Category: Delayed email notification  
Customer plan: Business  
Issue summary: Agents received assignment notifications about 20 minutes late.  
Root cause: Known issue `CD-KI-2026-014` caused delayed notification delivery.  
Resolution: Agent shared workaround to use in-app notification center and tagged ticket for monitoring.  
Required information: Workspace URL, examples of delayed tickets, timestamps, notification type.  
Useful knowledge source: `known_issues.md` delayed email notifications section.  
Final outcome: Customer used workaround while investigation continued.

## Ticket CD-TKT-2026-1007

Category: Enterprise outage  
Customer plan: Enterprise  
Issue summary: All agents could not access team inbox during business hours.  
Root cause: Regional API degradation affected inbox loading for high-volume workspaces.  
Resolution: Agent escalated as Urgent using `CD-INCIDENT-SUSPECTED`; Incident Command mitigated within 42 minutes.  
Required information: Workspace URL, affected feature, timestamps, region, business impact.  
Useful knowledge source: `enterprise_sla_policy.md` outage handling section.  
Final outcome: Service restored and Enterprise updates sent every 30 minutes.

## Ticket CD-TKT-2026-1008

Category: Account recovery  
Customer plan: Business  
Issue summary: Billing Admin left the company and no one could update payment details.  
Root cause: Only former employee had Billing Admin permission.  
Resolution: Agent verified Workspace Owner through company domain and recent invoice, then guided owner to assign a new Billing Admin.  
Required information: Workspace URL, old admin email, requester email, invoice number, role confirmation.  
Useful knowledge source: `account_recovery_policy.md` admin account recovery section.  
Final outcome: New Billing Admin added after verification.

## Ticket CD-TKT-2026-1009

Category: Privacy deletion request  
Customer plan: Enterprise  
Issue summary: Customer requested deletion of a former end user's profile and ticket history.  
Root cause: Data subject request submitted through verified admin.  
Resolution: Agent collected scope and escalated to Privacy Operations with `PRIV-DELETE-REQUEST`.  
Required information: Workspace URL, requester role, data subject email, deletion scope, deadline.  
Useful knowledge source: `privacy_policy_summary.md` data deletion requests section.  
Final outcome: Privacy Operations completed deletion workflow and confirmed allowed summary.

## Ticket CD-TKT-2026-1010

Category: Invoice download problem  
Customer plan: Pro  
Issue summary: Customer received `CD-INV-EXPORT-500` when downloading April invoice.  
Root cause: Invoice PDF generation failed after tax information update.  
Resolution: Billing Engineering regenerated invoice PDF and confirmed download.  
Required information: Invoice number, workspace URL, browser, billing email, error code.  
Useful knowledge source: `billing_faq.md` invoice download section and `known_issues.md` invoice PDF export error.  
Final outcome: Invoice downloaded successfully.

## Ticket CD-TKT-2026-1011

Category: Two-factor authentication issue  
Customer plan: Business  
Issue summary: Admin lost authenticator app after replacing phone.  
Root cause: User did not save backup codes.  
Resolution: Another Workspace Owner reset MFA from team security settings after verifying the requester internally.  
Required information: Login email, workspace URL, role, whether another owner was available.  
Useful knowledge source: `login_troubleshooting.md` two-factor authentication issue section.  
Final outcome: Admin enrolled new authenticator app.

## Ticket CD-TKT-2026-1012

Category: Plan downgrade  
Customer plan: Business  
Issue summary: Customer downgraded to Pro but was still billed at Business rate.  
Root cause: Downgrade job failed because an Enterprise integration add-on remained active.  
Resolution: Billing Operations removed incompatible add-on, applied downgrade, and issued prorated credit.  
Required information: Workspace URL, billing email, requested plan, invoice number, downgrade date.  
Useful knowledge source: `billing_faq.md` plan downgrade section.  
Final outcome: Plan corrected and credit applied to next invoice.

## Ticket CD-TKT-2026-1013

Category: Analytics slow loading  
Customer plan: Enterprise  
Issue summary: Dashboard took nearly one minute to load for a 12-month ticket report.  
Root cause: Known issue `CD-KI-2026-021` affected large workspaces with more than 500,000 tickets.  
Resolution: Agent suggested 30-day date range and team filters while Support Engineering monitored performance.  
Required information: Workspace URL, dashboard name, date range, ticket volume, timestamp.  
Useful knowledge source: `known_issues.md` analytics dashboard slow loading section.  
Final outcome: Customer used filtered reports until performance improved.

## Ticket CD-TKT-2026-1014

Category: Tax and VAT  
Customer plan: Business  
Issue summary: Customer asked why VAT appeared after updating billing address.  
Root cause: Tax calculation changed based on new billing country and missing VAT ID.  
Resolution: Agent explained where to update tax information and clarified that support cannot provide tax advice.  
Required information: Workspace URL, billing email, invoice number, billing country, tax ID status.  
Useful knowledge source: `billing_faq.md` tax and VAT questions section.  
Final outcome: Customer added VAT ID and downloaded updated invoice.

## Ticket CD-TKT-2026-1015

Category: Enterprise admin recovery  
Customer plan: Enterprise  
Issue summary: All admins were locked out after SSO certificate rotation.  
Root cause: New identity provider certificate was not uploaded to CloudDesk.  
Resolution: Enterprise Support verified Designated Support Contact, temporarily enabled recovery path, and helped upload new SAML certificate.  
Required information: Workspace URL, Designated Support Contact, identity provider, timestamp, business impact.  
Useful knowledge source: `account_recovery_policy.md` enterprise admin recovery section.  
Final outcome: Admin access restored and SSO tested successfully.
