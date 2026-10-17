# TAILWIND-4 diff review — response

**Last Updated:** 2026-10-12

Codex diff review of PR #74 (`feat/tailwind4` @ `3116064`). Model: `gpt-6-luna`, effort `high`; the owner's first choice `gpt-6.1-sol` returned HTTP 400 "not supported when using Codex with a ChatGPT account". Verdict: needs-attention (1 MAJOR, 1 MINOR). Both are about which elements the style spec targets; both targets are fixed by the brief, so neither changes code in this PR.

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | MAJOR | `e2e/tailwind4-styles.spec.ts:176`: the focus-ring check targets the Sidebar NavLink, which carries its own `focus-visible:ring-2 ring-accent ring-offset-2` (`Sidebar.tsx:67`), so `boxShadow !== 'none'` can pass without the global `*:focus-visible` rule | **Partly accepted, documented; spec unchanged.** Correct for the ring half. The outline half (`outlineStyle === 'none'` or transparent) still depends only on the global rule (`globals.css:281-282`): the NavLink has no `outline-*` class. The brief fixes this target (§4.2 item 6, Fable F2), so moving it is a brief change for L0. Recorded in the PR body under "Not verified". |
| 2 | MINOR | Touch target (`min-h-target`) and collision guards (`bg-surface`, `text-ink`, `rounded-lg`) use explicit classes | **Rejected.** By design: the brief labels the 44px check app-specific (§4.2 item 4, Codex C2), and item 5 exists to check that explicit token classes keep their v3 value after the `:root` collision fix. They were red at commit 2 where expected (body background, `rounded-lg`). |
