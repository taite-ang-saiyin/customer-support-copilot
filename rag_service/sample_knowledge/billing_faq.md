# CloudDesk Billing FAQ

## Overview

This FAQ helps support agents answer common billing questions for CloudDesk subscriptions, renewals, invoices, taxes, and payment methods.

## Failed Payments

Failed payments can occur because of expired cards, insufficient funds, bank fraud rules, or payment gateway timeouts. CloudDesk retries failed subscription payments up to three times over 7 days.

Support action:

- Ask the customer for workspace URL, billing email, invoice number, and approximate payment time.
- Check the invoice status: `open`, `past_due`, `paid`, or `void`.
- If the customer sees error `CD-PAY-402`, ask them to update the payment method and retry.
- If retry fails twice, escalate to Billing Operations with reason `PAYMENT-RETRY-FAILED`.

## Invoice Download

Admins and billing contacts can download invoices from `Settings > Billing > Invoices`. Invoice PDFs are generated after the invoice status is `paid` or `open`.

If the download button is missing, confirm that the user has Billing Admin or Workspace Owner permission. If the PDF returns error `CD-INV-EXPORT-500`, ask for the invoice number and browser details, then escalate to Billing Engineering.

## Subscription Renewal

Monthly subscriptions renew on the same calendar day each month. Annual subscriptions renew on the contract renewal date shown in `Settings > Billing > Subscription`.

CloudDesk sends renewal reminders 14 days and 3 days before annual renewal for Business and Enterprise plans. Free and Pro monthly renewals may not receive manual reminders.

## Plan Upgrade

Plan upgrades take effect immediately. The customer may receive a prorated charge for the remaining billing period.

Required information:

- Current plan.
- Requested new plan.
- Number of seats.
- Workspace URL.
- Confirmation from a Workspace Owner or Billing Admin.

Agents can guide the customer through self-service upgrades. Enterprise upgrades must be handled by the Account Team.

## Plan Downgrade

Plan downgrades usually take effect at the next renewal date. A downgrade may remove features such as advanced analytics, SSO, custom roles, or automation rule limits.

Before downgrade, tell the customer to export any reports they need and review feature limits. If the customer reports that a downgrade did not apply, create case `BILLING-DOWNGRADE-NOT-APPLIED`.

## Payment Method Update

Billing Admins can update payment details from `Settings > Billing > Payment Method`. CloudDesk accepts major credit cards and approved Enterprise invoice terms.

Agents must never collect full card numbers, CVV codes, bank login details, or card photos. If a customer cannot update payment details due to error `CD-PAY-METHOD-409`, ask them to try a private browser window and escalate if the error continues.

## Tax and VAT Questions

Tax and VAT are calculated based on the billing address, tax registration number, and local requirements. Customers can add or update tax IDs from `Settings > Billing > Tax Information`.

CloudDesk Support can explain where tax appears on the invoice but cannot provide tax advice. If a customer asks whether they should be charged tax, advise them to consult their tax professional.

## Duplicate Billing FAQ

If a customer says they were charged twice, confirm whether both charges are settled or one is pending. Pending authorizations are not completed charges and usually disappear automatically.

Ask for invoice numbers, charge dates, amount, currency, billing email, and last four card digits. Follow the refund policy for verified duplicate charges.

## Billing Contact Change

Workspace Owners can change the billing contact from `Settings > Billing > Billing Contact`.

If the owner has left the company, follow the account recovery policy. Agents should not change the billing contact based only on an email request from a non-admin user.
