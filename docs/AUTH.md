# Sign-in options

Nyavu supports three ways in. Email and password always work. The other two are opt-in
and controlled entirely by environment variables, so the interface only offers what is
actually configured — `/api/auth/methods` reports the truth and the browser hides the
rest.

## Google

Create an OAuth 2.0 Client ID (type: Web application) in the Google Cloud Console, add
the authorised redirect URI, then set:

| variable | value |
|---|---|
| `GOOGLE_CLIENT_ID` | `....apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | the client secret |
| `OAUTH_REDIRECT_BASE` | optional; defaults to the request origin |

Authorised redirect URI to register:

```
https://nyavu.onrender.com/api/auth/google/callback
```

The flow is the authorisation-code type with a `state` cookie. On callback Nyavu reads
`email`, `name` and `sub` from the userinfo endpoint, links an existing account by email
or creates one, and sets the same `pg_session` cookie the password flow uses. Accounts
created this way carry a random password hash that can never be used to sign in.

## Phone

A six-digit code is generated server-side, stored as a PBKDF2 hash with a five-minute
expiry and a five-attempt ceiling, and sent by SMS.

| provider | variables |
|---|---|
| Africa's Talking | `AT_USERNAME`, `AT_API_KEY`, optional `AT_SENDER_ID` |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` |

With neither configured the code is written to the server log and the API reports
`channel: "log"`. That keeps the flow testable locally, and it is never returned to the
client — an unconfigured deployment cannot be signed into by guessing, only by reading
the logs, which only the operator can do.

Phone accounts are keyed on a synthetic address of the form
`2547XXXXXXXX@phone.nyavu.local`. The primary identity for those accounts is the phone
column; the email is never shown and never receives mail.

## Number format

`normalise_phone` keeps digits and a leading `+`, and promotes local Kenyan forms
(`07...`, `01...`) to `+254...`. Anything shorter than nine digits is rejected.
