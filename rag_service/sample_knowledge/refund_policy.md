# CloudDesk Refund Policy

## Purpose

This policy explains when CloudDesk may issue refunds for SaaS subscription charges, add-ons, and usage-based billing. It is synthetic demo content for support training and RAG testing.

Agents must verify the billing event before discussing refund approval. Agents may say that a refund request will be reviewed, but must not promise a refund before verification is complete.

## Duplicate Charges

A duplicate charge occurs when the same workspace is billed twice for the same billing period, plan, invoice number, or payment attempt. Common indicators include two card charges with the same amount within 48 hours or two invoices for the same workspace ID and billing period.

Support action:

- Ask for the workspace URL, billing email, invoice numbers, charge dates, and last four digits of the payment card.
- Check the Billing Ledger for matching transaction IDs.
- If the duplicate is confirmed, create refund case type `BILLING-DUPLICATE-CHARGE`.
- If only one successful payment exists and the second item is a pending bank authorization, explain that pending authorizations usually expire automatically.

## Refund Eligibility

CloudDesk may approve refunds when a verified billing error occurred, such as duplicate billing, incorrect plan renewal after a confirmed cancellation, or a failed downgrade that continued billing at the prior plan.

Refunds may also be considered when a customer was charged after CloudDesk Support confirmed cancellation in writing. Attach the support ticket ID or cancellation confirmation to the refund case.

## Non-Refundable Cases

The following cases are normally not refundable:

- Unused time on a monthly subscription after the renewal date.
- Add-on usage already consumed, including AI response credits and archived ticket storage.
- Charges older than 90 days unless required by a written enterprise agreement.
- Fees caused by customer bank charges, currency conversion, or card issuer policies.
- Accounts closed for Terms of Service violations.

Agents may still document the request and escalate if the customer cites a signed contract, legal requirement, or executive approval.

## Refund Processing Time

Approved refunds are submitted within 2 business days after verification. Card refunds usually appear within 5 to 10 business days depending on the customer's bank.

ACH and wire refunds for Enterprise accounts may take 10 to 15 business days. If a refund has not appeared after 15 business days, escalate with case reason `REFUND-NOT-RECEIVED`.

## Required Customer Information

Collect only the minimum information needed:

- Workspace URL or workspace ID, such as `acme-demo.clouddesk.example`.
- Billing email, such as `billing@example.com`.
- Invoice number, such as `CD-INV-2026-04118`.
- Charge date, amount, and currency.
- Last four digits of the card or payment method nickname.
- Screenshot of the bank charge only if invoice matching fails. Ask the customer to hide full card numbers and unrelated transactions.

Never request a full card number, CVV, banking password, government ID, or customer account password.

## High-Value Refund Escalation

Refunds of USD 1,000 or more require Billing Operations approval. Refunds of USD 5,000 or more require Billing Operations and Finance Manager approval.

Escalate immediately when:

- The refund amount is over USD 1,000.
- The customer is on an Enterprise annual contract.
- The request involves a legal notice, chargeback, or procurement dispute.
- The customer claims a service outage caused financial loss.

Use escalation code `CD-BILL-ESC-HIGHVALUE` and include verified invoice details.

## Agent Language

Recommended phrasing:

"I can help review this charge. I will verify the invoice and payment records first, then we can confirm whether a refund is available."

Avoid:

"You will definitely receive a refund."

Agents must not promise a refund, refund amount, or processing date before the refund case is approved.
