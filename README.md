# sifventures.com

The SIF Ventures website, built from the SIF Ventures Design System (colors, type, logos and voice).
Plain HTML and CSS, no WordPress, no framework.

## Editing

- Page content: `src/pages/<page>.html`. The first line of each file holds its address, title and search description.
- Shared header and footer, including the legal disclaimer: `build.py`.
- Styles: `src/assets/css/site.css`. Brand colors and type are at the top.
- Links between pages are written `{{link:membership}}` so they work on any host.

Run `python3 build.py` to produce the site in `public/`, and commit `public/` with your change: the host serves it as is.
`python3 build.py --preview` produces a self-contained copy for a private review link.

## Page addresses

The new site keeps the WordPress addresses (`/about-us/`, `/membership/`, `/founding-membership/`,
`/club-membership/`, `/portfolio/`, `/events/`, `/community/`), so existing links keep working.
`vercel.json` forwards the few retired ones: `/deal-flow/` and `/registration/`.

## Members from Notion

The community page is built from the Notion database **SIF Members**. A person appears when both are true:

- **Website: Show** (checkbox) is ticked. This records that they agreed to be listed.
- **Conversion Status** is a member stage: Reserved, Collection, Payment in Progress, Paid, or Renewal Fee Due.

Moving someone up the funnel adds them; moving them to Park, Not a Fit or Closed removes them.
The card shows Name, the first role in Unvan, the first company in Şirket, LinkedIn, and the photo in
**Website Photo** (a files property). Optional **Website Title** / **Website Company** override the card text.

How it updates:

1. `scripts/sync_notion.py` runs at the start of every Vercel build. It reads Notion with the
   `NOTION_TOKEN` environment variable (a Notion internal integration with read access to SIF Members),
   writes `src/data/members.json` and downloads photos. Without the token it keeps the last list.
2. Instant: a Notion database automation on SIF Members, "When Conversion Status or Website: Show changes →
   Send webhook", pointed at a Vercel Deploy Hook URL. The page updates in about a minute.
3. Backup: `.github/workflows/refresh-members.yml` calls the same Deploy Hook every hour
   (store it as the `VERCEL_DEPLOY_HOOK` repository secret).

The Notion token and the Deploy Hook URL are secrets: keep them in Vercel and GitHub settings, never in the code.

## Copy rules

Investor-facing copy follows SIF's Terms & Conditions and the UK financial promotion rules
(FSMA 2000 s21, FPO 2005). The public site carries no returns, valuations, deal terms or minimum
tickets. Specific opportunities are shared only inside the private, certified member group.
Run new copy through the `sif-compliance-check` skill before publishing.

## Going live

1. Host: import this repository into Vercel (or Netlify). Vercel reads `vercel.json`.
2. Staging: add `new.sifventures.com` as a domain in the host, then add the CNAME record it shows in GoDaddy DNS.
3. Launch: add `sifventures.com` and `www.sifventures.com`, then change the A record for `@` and the
   CNAME for `www` in GoDaddy to the values the host shows. Leave the MX and TXT records alone: they run email.
4. Keep the WordPress hosting for a few weeks after launch as a fallback.

Open decisions before launch: where "Member login" points once WordPress is retired, and whether
membership fees stay public.
