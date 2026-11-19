# Kenyan coverage

Measured 2026-11-20 against the current snapshot.

- Kenyan institutions on our official list: 48
- reports total: 43,900
- hosts total: 339,433
- domains the feed maps to a Kenyan brand: 0 of 2,616 targeted domains
- hosts belonging to those domains: 0
- urls belonging to those domains: 0

The public lists are internationally weighted, so Kenyan campaigns are a small share of what we
can read. Impersonation of a local brand is still caught by the brand rules, but a domain that
spoofs a Kenyan brand and appears on no list is invisible to us until someone reports it.

## Brands the feed targets, by domain count


## Institutions on our list with no reported domain (48)

Not a defect: it means no feed entry maps to them, which is why their impersonations are caught
by name rules rather than by reports.

- Absa Kenya
- Airtel Kenya
- Co-operative Bank
- Credit Bank
- Daystar University
- Egerton University
- Equity Bank
- Family Bank
- HELB
- HFC
- Huduma Centre
- Independent Electoral and Boundaries Commission
- JKUAT
- Jamii Telecommunications
- Jumia Kenya
- KCB Bank
- Kabarak University
- Kenya Government
- Kenya Power
- Kenya Red Cross
- Kenya Revenue Authority
- Kenyatta University
- Kilimall
- Kingdom Bank
- M-Pesa
- Maseno University
- Moi University
- Multimedia University of Kenya
- NSSF Kenya
- NTSA
- Nairobi Water
- National Bank of Kenya
- Parliament of Kenya
- Prime Bank
- Royal Media Services
- SBM Bank Kenya
- SHA (Social Health Authority)
- Safaricom
- Sidian Bank
- Stanbic Bank Kenya

## What this means, plainly

Coverage is not thin; against reported domains it is absent. Every Kenyan detection we make is made by a
rule reading the name, not by a list that already knows the address. That is why impersonations of
Safaricom, KCB or M-Pesa are still caught, and also why a Kenyan campaign on a domain nobody reports stays
invisible until a person meets it.

Substring counting over hostnames was tried and rejected: "nic", "hf", "prime" and "chase" match thousands
of unrelated hosts, so a count built that way would be a number without a meaning.

## What would actually close it

1. A feed agreement with KE-CIRT or a Kenyan bank's fraud desk.
2. A curated list maintained by hand from public advisories, with dates and sources.
3. A reporting path of our own, moderated, which is the only one that produces data nobody else has.
