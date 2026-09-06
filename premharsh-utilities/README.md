# PremHarsh Utilities

The public app-information, privacy and support website for ten utility apps.
This directory contains only the static website, app icons, safe public issue
forms and a local validation script. It contains no Flutter app source, binaries,
production ad-unit IDs, credentials or user records.

Repository directory: <https://github.com/prxem-stack/prxem-stack.github.io/tree/main/premharsh-utilities>

Website URL: <https://prxem-stack.github.io/premharsh-utilities/>

## Pages

- Homepage: `/`
- App details: `/apps/photo/`, `/apps/milk/`, `/apps/shifts/`,
  `/apps/attendance/`, `/apps/fuel/`, `/apps/tailor/`, `/apps/recipes/`,
  `/apps/packing/`, `/apps/knitting/`, `/apps/room/`
- Corresponding app-specific policies: `/privacy/<app-id>/`
- Policy directory and website privacy: `/privacy/`
- Support: `/support/`

These paths are relative to the project Pages URL. No store links are advertised
until actual official listings are available. Store badges, download counts,
reviews and endorsements have not been invented.

## Check and preview

Run `python3 scripts/check_site.py` from this directory. It checks every local
HTML reference and fragment, metadata, all ten app/policy pairs, responsive CSS
rules, public-only content and the publisher declaration. It does not perform a
visual browser test, external link check or AdMob verification.

For a local preview, serve this directory with a static HTTP server. No package
installation, JavaScript bundle, framework or build step is needed.

## Publish with GitHub Pages

Publish the website files under `premharsh-utilities/` in the existing public
`prxem-stack/prxem-stack.github.io` repository on `main`. The account's GitHub
Pages hosting is already enabled. Keep the existing root website and its other
directories intact. Copy the three issue forms into the repository-root
`.github/ISSUE_TEMPLATE/` directory using `utilities_` filename prefixes, and
place the issue chooser configuration there. General blank issues stay enabled.
Verify the live homepage, a nested app page, a nested policy and the support forms
after deployment. The static canonical URLs and sitemap use the
`/premharsh-utilities/` path under `prxem-stack.github.io`.

Issue templates work after being committed to the default branch with Issues
enabled. Issues are public. These forms never ask for email addresses, app data
exports, customer details, identifiers or identity documents. They are suitable
for non-sensitive support and general privacy questions, not a private intake
channel for sensitive personal requests.

## app-ads.txt: project subpath is not root verification

The included file contains the requested public publisher declaration:

```
google.com, pub-7658767097946231, DIRECT, f08c47fec0942fa0
```

Publishing this directory serves its copy at
`https://prxem-stack.github.io/premharsh-utilities/app-ads.txt`.
**That does not establish that the file is available at the domain root**
`https://prxem-stack.github.io/app-ads.txt`.

AdMob discovers app-ads.txt using the developer website domain in a supported
store listing. A project path is not a substitute for the appropriate root file.
The existing account-root repository already contains the matching declaration
in its root `app-ads.txt`; that file is preserved. Verify the public root URL,
add the matching developer website to the store listings, and check AdMob's
crawler status separately. Repository content alone does not prove crawler
verification or full ad-serving approval.

Official setup guidance:
<https://support.google.com/admob/answer/9363762?hl=en>

## Privacy publication and app setup

The policies describe the current local utility records, the Google Mobile Ads
and UMP integration, user-chosen sharing, operating-system backups and public
GitHub support. They identify the publishing brand PremHarsh Utilities and its
GitHub maintainer; no private account email or invented legal entity is included.

After the Pages URLs are live, use each app's exact policy URL in its corresponding
AdMob Android/iOS app configuration and the stores. Publish the required consent
messages and verify the native consent experience separately. Hosting a policy
does not itself configure or approve an AdMob app, consent message or store release.

A dedicated private support/privacy channel and any store-required support email
remain separate release decisions. GitHub Issues is public and is not an email
address.

This website uses no analytics, website ads, tracking scripts, remote fonts or
external image assets. GitHub's own hosting and account processing is disclosed
and linked in the website privacy page.
