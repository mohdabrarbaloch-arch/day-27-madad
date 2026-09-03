# Madad — Usage Guide

How each role uses the platform.

## Donor

1. **Register** (or log in) — email + password, instant.
2. Browse **Explore** — filter by category, city, search, or sort (newest / most urgent / most raised).
3. Open a campaign, read the story + updates, and check the **public ledger**.
4. Click **Donate now** — pick a preset (PKR 1k–10k) or a custom amount, add an optional message, choose to stay anonymous.
5. A **pledge** is created with a receipt reference (e.g. `MAD-1A2B3C4D`). Transfer the amount to the campaign owner's bank account (shared by the owner out-of-band), then the owner confirms the receipt.
6. Track status under **Dashboard → My donations**. Cancel any pledge that's still unconfirmed.

## Campaign owner

1. **Dashboard → Start a campaign**: title, category, goal (PKR), city, hospital, and a detailed story (min 50 chars).
2. The campaign sits **pending** until an admin verifies the documents. If rejected, the dashboard shows the reason — fix and submit again.
3. Once **live**, share the campaign link (WhatsApp etc.).
4. When a donor pledges, the pledge appears under **Dashboard → Manage pledges** with the donor's reference and message.
5. After receiving the transfer in your bank account, click **Confirm receipt** — the amount is added to `raised` and appears on the public ledger.
6. Post **updates** on the campaign page as treatment progresses — receipts and doctor notes build donor trust.
7. The campaign **auto-closes at 100%**. You can also close it manually anytime.

## Admin

1. Log in with the seeded admin account (`admin@madad.pk` / password from env).
2. **Admin → Pending review**: verify (go live) or reject (reason required, shown to the owner).
3. **Admin → Live**: close any campaign that violates policy.
4. **Admin → Users**: suspend/unsuspend accounts (suspended users lose access immediately).
5. **Admin → Stats**: totals across campaigns, users and donations.

## Trust model (why this matters)

- Donations go **directly** to the campaign owner's bank account — Madad never holds money, which keeps the platform simple and honest.
- The **public ledger** makes every confirmed rupee traceable; anonymous donors are hidden but the amount and reference stay public.
- A campaign **cannot be self-funded** and **cannot raise beyond its goal** — both enforced at the API level.
