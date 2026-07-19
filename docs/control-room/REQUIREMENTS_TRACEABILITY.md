# Control Room — Requirements Traceability

Maps the directive's acceptance criteria (Read-Only Control Room brief, §13) and
key mandates to implementation and verifying tests. Test ids refer to
`tests/test_control_room.py` unless noted. **v2** adds a second table mapping
`docs/control-room/V2_LIVE_SYNC_SPEC.md`'s FR/NFR/acceptance items.

| # | Acceptance criterion | Implementation | Verification |
|---|---|---|---|
| 1 | Securely owner-authorized route exists | `owner_authorization.owner_required`, `control_room_routes.py` | `test_owner_by_email_sees_the_dashboard`, `test_owner_by_user_key_sees_the_dashboard`; live: owner render verified |
| 2 | Not publicly discoverable (nav/sitemap) | Standalone template; route not in `sitemap_xml` allowlist or `base.html` | `test_route_absent_from_public_sitemap`, `test_route_absent_from_public_navigation_template` |
| 3 | Data endpoints independently enforce owner auth | `@owner_required` on both page and `data.json` | `test_unauthenticated_data_endpoint_is_not_found`, `test_authenticated_non_owner_data_endpoint_is_not_found`, `test_owner_data_endpoint_returns_json_projection` |
| 4 | Useful overview from real sources | `control_room_projection.overview/governance_summary/initiatives` | `test_projection_declares_itself_read_only`; live: real data rendered (Bible v2.5, 2 active) |
| 5 | Source references + timestamps | `_source`, `source_ref` macro; every provider carries source/updated | live read_page shows source links + dates |
| 6 | Differentiate unknown/unavailable/stale/partial | status vocabulary + `pill()` macro (text + glyph, not colour alone) | `test_missing_source_renders_unavailable_not_favourable`, `test_documents_flag_missing_files_as_unavailable` |
| 7 | No manufactured completion percentages | No percentage computed anywhere | code review; provider returns counts/states only |
| 8 | Preserve implementation vs test vs deploy vs prod-verify | Delivery health separates recorded release from live probe | `test_delivery_never_claims_live_green` |
| 9 | Views for initiatives/documents/decisions/traceability/delivery/changes | Seven sections in template + providers | live read_page enumerates all sections |
| 10 | Unsupported integrations render truthful unavailable | `delivery_health.live_integration = unavailable`; `recent_changes` degrades | `test_delivery_never_claims_live_green`; prod path documented |
| 11 | No approval/edit/assign/deploy/agent-command/mutation capability | GET-only blueprint; projection never touches DB | `test_only_get_methods_are_registered`, `test_projection_never_touches_the_database_service` |
| 12 | No private docs/credentials in a public client bundle | Server-rendered; no secrets read; JS references no secrets | `test_no_secret_names_in_client_javascript` (site rules); code review |
| 13 | Follows design system, responsive, accessible | `control-room.css` Deep Navy Gold, semantic HTML, skip link, `th scope`, focus-visible, reduced-motion | desktop/mobile/dark screenshots; read_page semantics |
| 14 | Loading/empty/partial/stale/error/unauthorized/forbidden states | Section 7 of ARCHITECTURE.md; 404 for non-owner | `test_unauthenticated_page_is_not_found`, `test_authenticated_non_owner_page_is_not_found`, live fail-closed 404 |
| 15 | Focused auth/truthfulness/read-only/UI tests pass | `tests/test_control_room.py` (40) + `tests/test_azure_devops_read.py` (11) | all 51 pass |
| 16 | App suite + build remain healthy | Full suite 377 pass (1 pre-existing skip) | `python -m unittest discover -s tests` |
| 17 | Architecture/config/source-mapping documented | `docs/control-room/ARCHITECTURE.md` | this folder |
| 18 | Traceability from requirements to evidence | this matrix | — |

## Security mandates (§5–§6)

| Mandate | Implementation | Verification |
|---|---|---|
| Owner check server-side, no client-trusted fields | `is_owner` uses server-resolved identity only | `test_client_supplied_fields_cannot_elevate` |
| Fail-closed when unconfigured | empty allowlists ⇒ `is_owner` always False | `test_empty_allowlist_locks_everyone_out`; live empty-allowlist 404 |
| Unauthorized responses leak no data | 404 body checked for dashboard markers | leak assertions in the 404 tests; live check |
| noindex + not in sitemap | `_harden` headers; allowlist sitemap | `test_owner_responses_are_noindex_and_non_cacheable` |
| No mutation endpoints (even hidden) | GET-only | `test_only_get_methods_are_registered` |

## v2 — Live Repository Sync (`V2_LIVE_SYNC_SPEC.md`)

| ID | Requirement | Implementation | Verification |
|---|---|---|---|
| FR-1 | Pipeline generates the snapshot every build, never fails the build | `scripts/generate_control_room_snapshot.py`, `azure-pipelines.yml` step | `test_generator_produces_valid_schema_from_real_git`, `test_generator_never_raises_when_git_missing`, `test_generator_main_never_raises_and_exits_zero` |
| FR-2 | Recent Changes: live git (dev) vs snapshot (prod), labelled | `control_room_projection.recent_changes` tiering | `test_recent_changes_prefers_live_git_in_dev`, `test_recent_changes_falls_back_to_snapshot_when_git_unavailable`; live: "Live git" chip shown |
| FR-3 | Branches, main commits, active/completed PRs, pipeline runs, each linked | `services/azure_devops_read.py` five endpoints + normalizers | `test_successful_fetch_parses_all_collections`; live: Repository activity section |
| FR-4 | Deployment drift: up_to_date / behind (+list) / unknown | `control_room_projection._compute_drift` | `ControlRoomDriftTests` (5 tests: equal, behind-with-count, missing build, missing tip, SHA outside fetched window) |
| FR-5 | Every section shows its freshness tier + "as of" | `freshness_deploy`/`freshness_tier` macros; per-section chips | live read_page: chips present on Initiatives/Documents/Decisions/Traceability/Repository activity/Recent changes |
| FR-6 | Tier 1 cached ≤60s; 90s browser poll; stale labelled with original time | `CACHE_TTL_SECONDS`, `STALE_CACHE_MAX_AGE_SECONDS`; `control-room.js` `AUTO_REFRESH_INTERVAL_MS` | `test_cache_hit_within_ttl_avoids_a_second_network_call`, `test_stale_cache_served_when_refresh_fails_but_recent`, `test_old_cache_beyond_stale_window_is_unavailable` |
| FR-7 | Unconfigured/failure states name the cause, not a stack trace | `fetch_repository_activity` not_configured/unavailable notes | `test_not_configured_makes_zero_network_calls`, `test_credential_invalid_reported_without_leaking_pat_or_body`; live: exact env-var names shown |
| FR-8 | v1 behavior fully preserved | No v1 route/auth/provider signature removed | full v1 test classes still pass unchanged |
| NFR-1 | Read-only: no write HTTP methods, no ADO write calls | GET-only blueprint unchanged; adapter only calls `_safe_get` (GET) | `test_only_get_methods_are_registered`; code review: no POST/PUT/PATCH/DELETE verb in `azure_devops_read.py` |
| NFR-2 | Credential handling: server-side only, least privilege, never logged/rendered | `_auth_header` builds the header inline; never returned/logged | `test_pat_never_appears_in_a_successful_result`, `test_credential_invalid_reported_without_leaking_pat_or_body` |
| NFR-3 | Fail-safe: ADO outage never 500s the page or blanks Tier 0 | Independent try/except per endpoint; `build_projection` degrades `repository_activity` without touching other sections | `test_one_endpoint_failing_does_not_blank_the_others`, `test_build_projection_without_app_config_does_not_raise` |
| NFR-4 | No new dependency | `urllib.request`/`json`/`time` (stdlib only) | `requirements.txt` diff: none |
| NFR-5 | Tier 1 fetch bounded, doesn't block Tier 0 | `TIMEOUT_SECONDS=5` per call; Tier 0 (`build_identity`) computed independently of Tier 1 | code review; `repository_activity` failure isolated from `build_identity` |
| NFR-6 | Accessible: semantic structure, text+glyph status, reduced motion, no focus/scroll steal on poll | Reuses `pill()` macro; `cr-new-pill` is inline, non-focusable; auto-refresh never calls `.focus()`/`scrollIntoView` | live read_page semantics; manual reduced-motion CSS review |
| NFR-7 | Security posture unchanged; snapshot file not publicly reachable | `_harden` unchanged; snapshot outside `static/`, no catch-all route | `test_snapshot_file_is_not_publicly_reachable` |

## v2.1 — Initiative detail pop-out (owner request: "tell me in detail what each initiative is")

| Concern | Implementation | Verification |
|---|---|---|
| Plain-language detail per initiative | `_parse_initiative_detail` (Outcome→summary, structured sections); `initiative_details()` | `test_detail_parser_lifts_outcome_as_summary`, `test_detail_parser_keeps_meaningful_sections`, `test_initiative_details_covers_real_packages`; live modal |
| Skip plumbing (Writable files / Required reading) | `_DETAIL_SKIP_HEADINGS` | `test_detail_parser_skips_plumbing_sections`; live: absent from modal body |
| No AI paraphrase (determinism rule) | Pure source parsing; no model call | code review; content is verbatim README prose |
| Missing README handled | `has_readme=False` path | `test_detail_parser_returns_none_without_readme`, `test_initiative_details_missing_readme_is_graceful` |
| Lean poll payload (detail page-only) | Passed to template only, not `build_projection` | `test_detail_is_not_in_the_lean_json_projection` |
| No new endpoint / no path from input | Hidden server-rendered store; modal reads DOM | `test_only_get_methods_are_registered`; code review |
| Accessible dialog | body-level `role=dialog`, focus move/trap/restore, Escape/backdrop close, scroll lock, reduced-motion | `test_owner_page_includes_detail_modal_and_store`; live Playwright (focus + Escape + focus-restore verified, 0 console errors) |
| XSS-safe rendering | Jinja autoescape; `render_blocks` emits only escaped text in known tags | code review; no `|safe` on file content |

Acceptance criteria 1–2 (auto-refresh on deploy/poll) and 4 (unconfigured is
fully functional) were verified live in the dev server (screenshots on file);
criterion 2's "≤90s poll" is a code-level guarantee
(`AUTO_REFRESH_INTERVAL_MS`), not independently re-measured against a real
Azure DevOps push in this pass, since no live PAT was available in this
environment — see Known gaps in the completion report.
