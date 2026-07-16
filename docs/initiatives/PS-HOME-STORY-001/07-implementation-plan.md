# Implementation plan (ordered)

1. Branch `work/2026-07-16-homepage-three-scenes` from current main. ✔
2. Add `_build_home_context()` + switch `home()` to `homepage.html`;
   keep `/experience` on the old template.
3. Build partials + scoped CSS per 03-architecture.md.
4. Add tests (06-test-plan.md); run full suite.
5. Browser review-refine loop at all required widths + zoom + reduced motion.
6. Record 09-verification.md, write 10-handoff.md.
7. Azure PR → squash merge → pipeline → production verify → GitHub mirror.
   (Delivery through the existing Azure DevOps workflow — no direct-to-prod
   bypass. Pete pre-authorized completion without a review pause.)

Rollback: revert the merge commit (or point `home()` back to
`experience.html` — one-line change); no data or schema involved.
