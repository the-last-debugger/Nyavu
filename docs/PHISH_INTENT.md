# What the link is probably after

Komen's question, as I understand it: if we can say a link is bad, can we say what it is *for*?

Partly, and the limit is worth stating clearly. The page is never fetched, so intent is inferred
from the address alone: the name, the labels in front of it, the path, the ending. That is enough
to name a goal in most real phishing, because phish usually announce their goal in the URL.

## The taxonomy

Six goals, chosen because each is visible in an address and each corresponds to something a person
can lose:

| goal | named by words like | what is taken |
| --- | --- | --- |
| get a password or a one-time code | login, verify, account, update, otp, unlock, recover | access to an account |
| take an M-Pesa PIN or a payment | mpesa, paybill, till, wallet, invoice, refund, deposit | money, directly |
| collect identity or tax details | kra, ecitizen, ntsa, helb, huduma, passport | identity, and the refund that follows |
| take a deposit on an investment | invest, crypto, forex, profit, earn | money, by consent |
| charge a fee for a parcel that is not coming | parcel, delivery, tracking, courier | a small, plausible payment |
| collect application details for a job or a loan | job, vacancy, loan, grant, apply | identity and an upfront fee |

This follows how phishing is categorised in practice: the
[APWG phishing activity trends](https://docs.apwg.org/reports/apwg_trends_report_q3_2023.pdf) groups
attacks by what the attacker is after (credentials, payment, malware), and the academic work on
inferring phishing intent from the page
([PhishIntentionLLM](https://export.arxiv.org/pdf/2507.15419)) uses much the same categories, which
is precisely why it reads pages and we do not.

## The rule for the copy

1. **Name what is taken, not the technique.** "Get a password", not "credential harvesting".
2. **Say "looks", never "is".** The name is evidence of shape, not proof of purpose.
3. **One sentence, one goal.** The other candidates go in the fold, listed, with the word that
   pointed at them, so the reader can see why.
4. **No disclaimer in the card.** The fact that nothing is fetched is true and available on request;
   it does not need to be volunteered under every verdict.
5. **Write brand names as their owners write them.** M-Pesa, KRA, eCitizen, WhatsApp.

## What it produces

| address | line |
| --- | --- |
| `mpesa.co.ke.verify-account.top` | Looks built to imitate M-Pesa and get a password or a one-time code. |
| `kra-refund.go.ke.ecitizen-tax.top` | Looks built to imitate KRA and collect identity or tax details. |
| `kabarak.ac.ke.verify-account.top` | Looks built to imitate Kabarak University and get a password or a one-time code. |
| an address with no legible cue | No goal is legible from the name alone. That is not the same as harmless. |

Goals are ranked by how many words in the address point at them, so a `kra` address with `refund`
and `ecitizen` reads as identity theft rather than as a payment.

## Where it appears

- a **likely goal** line under the verdict, above the reasons;
- the full list in "How that was worked out", each goal with the word that named it.

## Not done

- no page content, so no confirmation of intent;
- no inference from the sender, which would need an integration;
- no "this targets you specifically": we cannot see the campaign, only the address.
