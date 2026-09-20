---
document: refund-policy
category: policy
version: v4
effective_date: 2026-08-01
product: all
---

# Refund Policy v4

## Eligibility
- Orders delivered within last 30 days are eligible for refund.
- Orders must be in DELIVERED status; SHIPPED orders cannot be refunded until delivered.
- Damaged or defective products are eligible within 14 days with evidence.
- Refunds for orders cancelled before shipment are automatic within 3 business days.

## Processing Timeline
- Refunds are processed within 5-7 business days after approval.
- Funds appearance depends on payment provider: additional 2-3 business days.
- Customer will receive email notification when refund is initiated.

## Non-refundable
- Digital gift cards, clearance items marked final-sale.
- Orders already refunded.

## Process
1. Check order status via get_order
2. Verify eligibility via check_refund_eligibility
3. Create refund request via create_refund_request
4. Disputed refunds must be escalated to human.

## Citation
Always cite `refund-policy v4 (2026-08-01)` when explaining timelines or eligibility.
