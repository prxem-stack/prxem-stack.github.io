# Official-source update pipeline

Every six hours, or via Actions > Check official prop firm sources > Run workflow,
the job checks the allowlisted sources in live-manifest.json. App refresh downloads
the last completed check. A public mobile client cannot trigger GitHub jobs and
contains no GitHub token. Scheduling may be delayed by GitHub.

live.json is valid for 18 hours. Expired offers are excluded. Failed or changed
sources are excluded from offers and placed in review.json. A successful job does
not mean that every source was reachable or every rule was verified.

## Review and approval

1. Open each official source and confirm code, amount, customer eligibility,
   purchase cohort, model, region, account size, date and exclusions.
2. Compare the whole fetched page against the proposed record. Never approve a
   hash simply because the page fetched or a few keywords matched.
3. Put the reviewed page's sha256 from review.json into approvedHashes for its URL.
4. For rule records, check EVERY source and account applicability before adding
   a patch. Missing cohort/stage/cycle means leave pending. No automatic numeric
   rule extraction is enabled. Android accepts reviewed patches only for daily,
   maxl, t1 and t2 (fractions, not percent integers). Other fields require a client
   update. Custom profiles are never patched. A retracted patch restores bundled
   values on the next refresh. No numeric model patch is approved in this initial
   manifest: all 27 model records still require account-specific rule review.
5. Commit the manifest. The push triggers a fresh check before publication.

New promotions require review/manifest additions; this is a source-change and
verified-publication pipeline, not an autonomous web-research service. Whole-page
hashes are conservative: navigation/marketing changes may also require review.
No failed check advances a record's approval hash. No source text is executed.

The offers currently in the app were manually researched on 6 October 2026.
Until their fetched content has been matched and approved, the live feed correctly
withholds them rather than presenting old bundled coupons as live.
