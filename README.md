# sifventures.com

The SIF Ventures website, built from the SIF Ventures Design System (colors, type, logos and voice).
Plain HTML and CSS, no WordPress, no framework.

## Editing content: Notion

All words on the site live in Notion, on the page **SIF Home > SIF Website**:

| Table | What it holds |
|---|---|
| Site Copy | Every headline, paragraph, button and question, one row each (edit **Text**) |
| Events | Name, date, time, location, description, RSVP button. Upcoming and Recent are split by date |
| Testimonials | Home page quotes. **Featured** picks the large one |
| Partners, Leadership | Home page partners, About page team |
| Settings | Contact email, member login link, LinkedIn |
| Members on the site | A view of **SIF Members** |

Rules: Site Copy rows publish only when **Status = Live** (Editing keeps the current text).
Every publish runs a compliance check; a row with return figures, IRR, guarantees, valuations,
minimum tickets or inducements to invest is not published and is marked **Check = Blocked** with
the reason. The footer's legal disclaimer stays in `build.py` on purpose.

`scripts/sync_notion.py` reads Notion into `src/data/content.json` at the start of every build.
`src/data/content.json` in the repository is the last synced copy, so the site still builds
without Notion access.

## Editing layout and code

- Page layout: `src/pages/<page>.html`, with `{{t:key}}` slots for Site Copy texts.
- Header, footer and section builders: `build.py`.
- Styles: `src/assets/css/site.css`. Brand colors and type are at the top.

Run `python3 build.py` to produce the site in `public/`.
`python3 build.py --preview` produces a self-contained copy for a private review link.

## Page addresses

The new site keeps the WordPress addresses (`/about-us/`, `/membership/`, `/founding-membership/`,
`/club-membership/`, `/portfolio/`, `/events/`, `/community/`), so existing links keep working.
`vercel.json` forwards the few retired ones: `/deal-flow/` and `/registration/`.

## Members from Notion

The community page lists people from **SIF Members** when **Website: Show** (checkbox) is ticked
and **Conversion Status** is Reserved, Collection, Payment in Progress, Paid or Renewal Fee Due.
Cards show Name, the first role in Unvan, the first company in Şirket, LinkedIn, and the photo in
**Website Photo** (files). Optional **Website Title** / **Website Company** override the card text.
Until the Website: Show checkbox exists, the sync keeps the current list.

## How updates go live

1. Vercel runs `scripts/sync_notion.py` then `build.py` on every deploy. It needs `NOTION_TOKEN`:
   a Notion internal integration shared with SIF Website and SIF Members (read, plus update for
   the Check columns).
2. **Publish button:** on the SIF Website page, a Notion button with the action "Send webhook"
   to a Vercel Deploy Hook URL. The site updates in about a minute.
3. **Members:** a Notion automation on SIF Members, "When Conversion Status or Website: Show
   changes, send webhook", to the same Deploy Hook.
4. **Backup:** `.github/workflows/refresh-members.yml` calls the Deploy Hook every hour
   (repository secret `VERCEL_DEPLOY_HOOK`). It also rolls finished events into Recent.

The Notion token and the Deploy Hook URL are secrets: keep them in Vercel and GitHub settings.

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
