---
name: project-no-sharing-public-admin
description: "apps/public and apps/admin must share no code — no shared package, no cross-app imports, duplicate patterns instead."
metadata: 
  node_type: memory
  type: project
  originSessionId: db33c387-0ddb-4bab-9fd7-160cf6c0b34b
  modified: 2026-08-12T07:13:24.032Z
---

`apps/public` (public site) and `apps/admin` (admin UI) are two separate applications. They must
share no code: no repo-level shared package, no cross-app imports, no common DTO-type module, no
extracted logger module. Stated by the user 2026-08-12 while planning the public-site move.

**Why:** they are different applications with different audiences and lifecycles. The user does not
want them mixed. Coupling them would make one app's change break the other.

**How to apply:** when a pattern exists in one app and the other needs it (logger, session helper,
DTO types), copy the pattern and let each app own its copy. Never extract it upward. A `shared/`
directory inside either app is Nuxt 4's own isomorphic `app/`+`server/` convention — it is
app-internal and does not violate this rule. `e2e/` is a test suite, not an application, so it may
drive both. See [[project-public-site-integration-plan]].
