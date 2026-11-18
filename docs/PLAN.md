# WineTracker — Plan & Decisions

A personal wine cellar tracker: what bottles I have, when/where/with whom I drank them,
and how my experience of each bottle compares with my general perception of the wine.
Web first (Dash), mobile later (PWA, then native) on the same API.

## Product decisions

| Topic | Decision |
|---|---|
| Rating scale | 0–10 in half steps, shown as **wine glasses** (empty / half / full). Stored as integer half-points `0..20`. |
| General rating | Set manually per wine. Each consumed bottle gets its own rating, pre-filled with the general rating, so drift between perception and experience is visible. |
| Occasion participants | Both connected friends (app users) and plain contacts (not on the app; can be invited later and linked). |
| Friend visibility | Friends see occasions they took part in, plus my wine impressions and ratings. **Never** cellar inventory (bottle counts), prices or stores. |
| Hosting | AWS (target: ECS Fargate or App Runner + RDS MySQL 8 + Secrets Manager). |
| Database | Existing MySQL 8 instance (connection via `WT_DATABASE_URL`). |
| Auth | Email + password (Argon2) **and** Google / Apple sign-in (OIDC ID-token verification). |
| Languages | English (prices in USD) and Brazilian Portuguese (prices in BRL). Each price stores its own currency. |
| Repository | https://github.com/rafaeldobbin/WineTracker |

## Naming

- **Wine** = the product. Fields: *Nickname* (how I call it), *Official name* (label), producer,
  region, grapes (blend with %), type (red, white, rosé, sparkling, fortified, dessert, orange),
  general notes, general rating.
- **Bottle** = a physical bottle of a wine. *Vintage* (not "year"), purchase date, price + currency,
  store, cellar location, status (in cellar / consumed / gifted / lost), barcode.
- **Occasion** = a moment I drank something: date, meal (brunch, lunch, afternoon, tasting, dinner),
  city, country, place type (restaurant, my house, friend's house, family), place name, notes,
  participants, bottles opened (each with its own rating + tasting notes).

## Architecture

```
Dash web UI ──┐
              ├── HTTPS/JSON ──> FastAPI (api) ──> services ──> repositories ──> MySQL
Mobile (later)┘
```

- `winetracker.api` — FastAPI routers, request/response schemas, auth dependencies.
- `winetracker.services` — business rules (rating defaults, visibility, invitations).
- `winetracker.repositories` — SQLAlchemy 2.0 data access.
- `winetracker.models` — ORM models; schema evolves only through Alembic migrations.
- `winetracker.web` — Dash app. Talks **only** to the API, so a mobile client is a drop-in peer.
- Tooling: pytest, ruff, mypy, GitHub Actions; 12-factor config via `WT_*` env vars.
- Accessibility: WCAG 2.2 AA — keyboard navigable, labelled controls, ≥4.5:1 contrast,
  nothing conveyed by colour alone, rating glasses expose `aria-label="7.5 of 10"`.

## Roadmap

1. ✅ **Foundation** — repo, config, DB layer, full schema + migration, email/password auth, Dash shell, i18n, glass rating component, CI.
2. ✅ **Cellar** — wines (blends, producer/region/country), bottles (bulk add, status, drinking window, store, location), seeded grapes/regions, search and filters, grouped bottle table.
3. ✅ **Occasions & ratings** — occasions (when, where, who, food, notes), several wines each with its own rating pre-filled from the general rating, "Open a bottle" from the cellar, bottles return to the cellar when removed or the occasion is deleted, tastings per wine with perception-vs-experience.
4. **Friends** — invitations, requests, visibility rules, friends feed, Google/Apple sign-in.
5. **Polish** — dashboard/stats, PWA install, accessibility audit (axe).
6. **Barcode** — browser camera scanning (ZXing), lookup, quick add.
7. **AWS deploy** — container image, RDS, Secrets Manager, CI/CD.
8. **Native mobile app** on the same API.

## Feature backlog (proposed)

Drinking window + "drink soon" list · cellar rack/shelf location · label photos ·
wishlist · food pairing per occasion · CSV export · "buy again".
