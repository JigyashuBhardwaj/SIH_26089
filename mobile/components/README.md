# components/

Reusable, presentation-only React Native components shared between the
User and Worker flows. No navigation, no direct API calls, no business
logic — those live in `features/`, `services/`, and `../shared/`.

- **KarmanyaLogo.tsx** — the brand mark/wordmark used on splash, role
  selection, and both login screens.
- **RoleCard.tsx** — the role-selection cards (User/Worker).
- **FeatureCard.tsx** — the grid cards on User Home / Worker Home.
- **ProfileMenu.tsx** — the top-right profile icon + Logout menu, shared
  by both home screens.
- **ComingSoonDialog.tsx** — the single reusable "Coming Soon" modal used
  by every non-functional feature across both flows.
