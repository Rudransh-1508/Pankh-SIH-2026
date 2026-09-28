# Our own PostgreSQL and authentication in FastAPI, not Supabase

The verification layer, Consent ledger and audit trail need transactions and access rules that live in one place. Splitting them between FastAPI and Supabase row-level security would scatter the rules. Students sign in with a mobile number and OTP, since many do not have or use email, and link DigiLocker to prove identity. There are no passwords.

## Considered Options

- **Keep Supabase** (used by the earlier prototype): rejected because authorisation logic would live partly in database policies and partly in the backend.
