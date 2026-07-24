# Controlling-authority Markdown conversion manifest

**Migration date:** 2026-07-24
**Scope:** Bible v2.9 and Roadmap v2.8 format migration only. Their semantic
versions remain 2.9 and 2.8. The original owner-approved Word files are frozen,
non-controlling source snapshots and are not edited by this migration.

## Conversion method

`tools/convert_authority_docx_to_markdown.py` deterministically walks body
paragraphs and tables in document order, preserves headings, true Word lists,
callout/quote paragraphs, captions, practical external links, and meaningful
inline image references. It reuses an existing repository image when the
SHA-256 matches and writes only unique embedded diagrams to the governed
`docs/governance/authority-media/` path. Automatic Word TOC/page-number field
artifacts are omitted; they are not authority content. Ordered-list counters
restart at true list boundaries, including an intervening non-list paragraph,
table, heading, or a new top-level numbering sequence.

The Markdown outputs contain only the corresponding frozen DOCX body after
that non-authority field cleanup. No addendum is appended to Roadmap v2.8: the
planned AI evaluation gate is recorded in its initiative, backlog, and current
governance pointers rather than changing the semantic content of the locked
Roadmap.

## Equivalence record

| Authority | Controlling Markdown | Markdown SHA-256 | Frozen DOCX source snapshot | DOCX SHA-256 | Body paragraphs | Tables | Inline images | Unique extracted diagrams | Lists |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Bible v2.9 | `docs/governance/PeerSlate_Company_and_Product_Bible_v2.9.md` | `21DDFB3382E552DF38E2591280001BD503C37DAD349ADE56DC06820845173C21` | `docs/governance/PeerSlate_Company_and_Product_Bible_v2.9.docx` | `1BB3DF535B2A7478D36C539521D64E452A01B163FEBE367615A96F345459224F` | 979 | 92 | 10 | 4 | 312 |
| Roadmap v2.8 | `docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.md` | `BD9AC419B0BAB577181CEAD8A0B6D19A8E9AFD51006A78702D0F0D303A957AC7` | `docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.docx` | `612C23CF21CBA4A58905E77B067ADB82FF8A7BEA5A24A107742C973FE48495A1` | 1268 | 119 | 1 | 1 | 490 |

## Source and output checks

1. The source DOCX hashes above must remain exact. Their XML retains the
   approved current/locked status, authority language, version headers/footers,
   canonical Save Moment and derived-Journal content, and the existing required
   / forbidden phrase evidence.
2. The controlling Markdown hashes above must remain exact unless a controlled
   authority change updates both `CURRENT_BASELINE.yaml` and this manifest.
3. The Markdown contains the same source-body paragraph/table/image counts as
   the frozen DOCX, except automatic Word TOC/page-number field artifacts that
   are intentionally non-authority content. No Roadmap addendum is permitted.
4. Markdown image links must resolve to either existing approved repository
   assets or the governed unique diagram paths. The four Bible-only diagrams
   and one Roadmap-only architecture diagram are retained under
   `docs/governance/authority-media/`; matched images remain linked to their
   pre-existing approved assets.

## Reproduction commands

```powershell
$py = 'C:\Users\peter\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py tools/convert_authority_docx_to_markdown.py docs/governance/PeerSlate_Company_and_Product_Bible_v2.9.docx docs/governance/PeerSlate_Company_and_Product_Bible_v2.9.md --media-dir docs/governance/authority-media/bible-v2.9
& $py tools/convert_authority_docx_to_markdown.py docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.docx docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.8.md --media-dir docs/governance/authority-media/roadmap-v2.8
```

Run the governing-pointer tests after any controlled update. Do not edit a
frozen DOCX to "refresh" this migration.
