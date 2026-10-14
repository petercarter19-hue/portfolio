"""One read-only Guide projection over the existing intake and draft records."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from uuid import NAMESPACE_URL, UUID, uuid5
from services.resume_publication_projection import (
    RESUME_CORE_SECTIONS, RESUME_BASE_SECTION_ORDER, RESUME_SECTION_LABELS,
    resume_section_for, resume_section_order,
)


GUIDE_SECTIONS = RESUME_CORE_SECTIONS
GUIDE_SECTION_ORDER = RESUME_BASE_SECTION_ORDER


def model_resume_values(record_type, values):
    """Project links are private literal strings, never model inputs (269ab17)."""
    result = deepcopy(values)
    if record_type == "project":
        result.pop("project_url",None)
        result.pop("additional_project_urls",None)
    return result


def _json(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def bind_item_identities(owner, snapshot, *, privacy_repair=False):
    """Compute deterministic annotations; callers own persistence or detached reads."""
    rows = snapshot.get("proposals") or {}
    completed, visiting, ordinals, used = set(),set(),{},set()
    for row in rows.values():
        refs = [row.get("item_ref"),*(row.get("identity_aliases") if isinstance(row.get("identity_aliases"),list) else [])]
        used.update(ref for ref in refs if isinstance(ref,str))

    def bind(key):
        if key in completed:
            return
        if key in visiting:
            if privacy_repair:
                return  # A Guide-only history defect cannot veto source deletion.
            raise ValueError("Guide proposal identity history contains a cycle")
        row = rows[key]
        binding, meta = row.get("binding") or {},row.get("resume_conversation_v1") or {}
        if not isinstance(row.get("proposal_key"),str) or not isinstance(binding.get("source_key"),str):
            completed.add(key)
            return  # Historical incomplete rows do not gain invented source authority.
        visiting.add(key)
        previous_key = meta.get("revision_of")
        previous = rows.get(previous_key)
        if previous is not None:
            bind(previous_key)
        existing = row.get("item_ref")
        if existing is not None:
            try:
                UUID(existing)
            except (ValueError,TypeError,AttributeError):
                if not privacy_repair:
                    raise
                existing = None
        aliases = set(row.get("identity_aliases") or [])
        if privacy_repair:
            valid = set()
            for alias in aliases:
                try:
                    UUID(alias); valid.add(alias)
                except (ValueError,TypeError,AttributeError):
                    pass
            aliases = valid
        target = row.get("target_key")
        if target:
            reference = target
            if existing and existing != reference:
                aliases.add(existing)
        elif previous and previous.get("item_ref"):
            reference = previous["item_ref"]
        elif existing:
            reference = existing
        else:
            anchor = meta.get("record_anchor") or next(iter(meta.get("unit_ids") or []),None)
            anchor = anchor if anchor is not None else [row.get("span_start"),row.get("span_end")]
            group = _json([binding["source_key"],anchor])
            ordinal = ordinals.get(group,0)
            reference = str(uuid5(NAMESPACE_URL,"peerslate-guide-item:" + _json([owner,binding["source_key"],anchor,ordinal])))
            while reference in used:
                ordinal += 1
                reference = str(uuid5(NAMESPACE_URL,"peerslate-guide-item:" + _json([owner,binding["source_key"],anchor,ordinal])))
            ordinals[group] = ordinal + 1
        if previous and previous.get("item_ref") != reference and previous.get("item_ref"):
            aliases.add(previous["item_ref"])
        revision = row.get("revision")
        revision = revision if type(revision) is int and revision > 0 else 1
        if previous:
            prior = previous.get("revision")
            prior = prior if type(prior) is int and prior > 0 else 1
            revision = max(revision,prior+1)
        row["item_ref"],row["revision"] = reference,revision
        row["identity_aliases"] = sorted(aliases - {reference})
        used.add(reference); completed.add(key); visiting.remove(key)

    for key in sorted(rows,key=lambda key:(rows[key].get("created_at") or "",key)):
        bind(key)


def _section(record_type, metadata=None, values=None, *, story_bound=False, proposed=False):
    metadata = metadata or {}
    return resume_section_for(record_type, values, presentation_section=metadata.get("presentation_section"),
        story_bound=story_bound, proposed=proposed)


def _evidence(snapshot, row):
    binding = row.get("binding") or {}
    source = snapshot.get("sources",{}).get(binding.get("source_key"))
    live = bool(source and source.get("state")=="active" and source.get("version")==binding.get("source_version"))
    result = {"source_key":binding.get("source_key"),"source_version":binding.get("source_version"),
              "span":[row.get("span_start"),row.get("span_end")],"available":live}
    if live:
        text,quote = source.get("text"),row.get("quote")
        start,end = row.get("span_start"),row.get("span_end")
        if (isinstance(text,str) and isinstance(quote,str) and type(start) is int and type(end) is int
                and 0 <= start <= end <= len(text) and text[start:end]==quote):
            result["quote"] = quote
    return result


def _evidence_history(snapshot, row):
    result,seen,visiting = [],set(),set()
    def collect(current):
        key = current.get("proposal_key")
        if key in visiting:
            raise ValueError("Guide evidence history contains a cycle")
        visiting.add(key)
        previous = snapshot.get("proposals",{}).get((current.get("resume_conversation_v1") or {}).get("revision_of"))
        if previous is not None:
            collect(previous)
        evidence = _evidence(snapshot,current)
        identity = _json([evidence["source_key"],evidence["source_version"],evidence["span"]])
        if identity not in seen:
            result.append(evidence); seen.add(identity)
        visiting.remove(key)
    collect(row)
    return result


def project_working_set(owner, snapshot, canonical_items, draft_version, *, history=None):
    """Detached tree, derived counts and a token; no extractor, persistence or save."""
    history = history or {}
    # Pre-upgrade rows use precisely the commit formula, without persisting on GET.
    snapshot = deepcopy(snapshot)
    bind_item_identities(owner,snapshot)
    nodes,unplaced,legacy = {},[],[]
    for source_item in canonical_items:
        item = deepcopy(source_item)
        key = item["record_key"]
        values = {**(item.get("values") or {}), **(item.get("proposed_values") or {})}
        section = _section(item["record_type"],{"presentation_section":history.get("section",{}).get(key)
            or item.get("presentation_section") or (item.get("values") or {}).get("presentation_section")},
            values, story_bound=item.get("story_bound") is True)
        hidden = history.get("inclusion",{}).get(key) is True
        nodes[key] = {"item_ref":key,"identity_aliases":[],"origin":"saved","state":"hidden" if hidden else "saved",
            "has_draft":item.get("has_draft") is True,
            "update_waiting":False,
            "record_type":item["record_type"],"section":section,"values":{
                **deepcopy(item.get("values") or {}),
                **(deepcopy(item.get("proposed_values") or {}) if item.get("has_draft") else {})},
            "saved_revision":item.get("content_token"),
            "saved_content_version":item.get("content_version"),"saved_access_revision":item.get("access_revision"),
            "parent_ref":item.get("parent_key"),"proposal_key":None,"revision":None,"proposals":[],"evidence":[],"children":[],
            **({"evidence_refs":deepcopy(item["evidence_refs"]),"evidence_refs_manual":item.get("evidence_refs_manual") is True}
                if "evidence_refs" in item else {})}
    rows = snapshot.get("proposals") or {}
    for row in sorted(rows.values(),key=lambda row:(row.get("created_at") or "",row.get("proposal_key") or "")):
        target = row.get("saved_record_key") or row.get("target_key")
        if row.get("state")=="accepted" and target in nodes:
            node = nodes[target]
            node["evidence"].extend(_evidence_history(snapshot,row))
            node["identity_aliases"].extend([ref for ref in [row.get("item_ref"),*(row.get("identity_aliases") or [])]
                                             if ref and ref != target])
            continue
        if row.get("superseded_by") or row.get("state") not in {"pending","hidden","rejected"}:
            continue
        meta = row.get("resume_conversation_v1") or {}
        reference = target if target in nodes else row.get("item_ref")
        if not reference:
            reference = str(uuid5(NAMESPACE_URL,"peerslate-guide-legacy:" + _json([owner,row.get("proposal_key")])))
        section = _section(row["record_type"],meta,row.get("proposed_values") or {},proposed=True)
        if row["state"]=="rejected" and (target in nodes or section != "unplaced"):
            legacy.append({"item_ref":reference,"proposal_key":row["proposal_key"],"state":"declined"})
            continue
        pending_hidden = row["state"] == "pending" and row.get("guide_hidden") is True
        state = "skipped" if row["state"]=="rejected" else ("hidden" if row["state"]=="hidden" or pending_hidden else "waiting")
        if reference not in nodes:
            nodes[reference] = {"item_ref":reference,"identity_aliases":list(row.get("identity_aliases") or []),
                "origin":"pending","state":state,"record_type":row["record_type"],"section":section,
                "values":deepcopy(row.get("proposed_values") or {}),"saved_revision":None,
                "parent_ref":(row.get("proposed_values") or {}).get("suggested_parent_key"),
                "proposal_key":row["proposal_key"],"revision":row.get("revision") or 1,
                "proposals":[],"evidence":[],"children":[]}
        node = nodes[reference]
        if node["origin"] == "saved":
            node["update_waiting"] = node["update_waiting"] or (row["state"] == "pending" and not pending_hidden)
        else:
            node["state"] = state
        node["proposals"].append({"proposal_key":row["proposal_key"],"revision":row.get("revision") or 1,
            "values":deepcopy(row.get("proposed_values") or {}),"kind":row.get("kind"),"state":row["state"]})
        node["evidence"].extend(_evidence_history(snapshot,row))
        node["proposal_key"] = row["proposal_key"] if len(node["proposals"])==1 else None
        node["revision"] = row.get("revision") or 1 if len(node["proposals"])==1 else None
    active_sources = []
    accounted = set()
    for row in rows.values():
        if row.get("state") not in {"pending","accepted","rejected","hidden"}:
            continue
        meta = row.get("resume_conversation_v1") or {}
        source_key = (row.get("binding") or {}).get("source_key")
        accounted.update((source_key,unit_id) for unit_id in meta.get("unit_ids") or [])
        accounted.update((ref.get("source_key"),ref.get("unit_id")) for ref in meta.get("source_refs") or [])
    for source in sorted(snapshot.get("sources",{}).values(),key=lambda row:(row.get("created_at") or "",row["source_key"])):
        if source.get("state") != "active":
            continue
        meta = (source.get("structured_values") or {}).get("resume_conversation_v1") or {}
        units = meta.get("source_units") or []
        pages = {unit.get("page") for unit in units if type(unit.get("page")) is int and unit["page"]>0}
        active_sources.append({"source_key":source["source_key"],"source_version":source.get("version"),
            "kind":source.get("kind"),"state":"active","complete":meta.get("complete"),
            "page_count":len(meta["pages"]) if isinstance(meta.get("pages"),(list,tuple)) and meta["pages"] else None,
            "text_page_count":len(pages) if pages else None,"unit_count":len(units),
            "organization":deepcopy(meta.get("organization") or {"state":"not_started"})})
        for unit in units:
            if unit.get("kind") != "content" or (source["source_key"],unit.get("unit_id")) in accounted:
                continue
            reference = str(uuid5(NAMESPACE_URL,"peerslate-guide-source-unit:"+_json([owner,source["source_key"],unit.get("unit_id")])))
            state = "skipped" if unit.get("disposition") in {"left_out","skipped"} else "waiting"
            evidence_row = {"binding":{"source_key":source["source_key"],"source_version":source.get("version")},
                "span_start":unit.get("span_start"),"span_end":unit.get("span_end"),"quote":unit.get("text")}
            nodes[reference] = {"item_ref":reference,"identity_aliases":[],"origin":"source","state":state,
                "record_type":"unspecified","section":"unplaced","values":{"text":unit.get("text")},
                "saved_revision":None,"parent_ref":None,"proposal_key":None,"revision":source.get("version"),
                "source_unit_ref":unit.get("unit_id"),"proposals":[],"evidence":[_evidence(snapshot,evidence_row)],"children":[]}
    children = set()
    for key,node in nodes.items():
        parent = nodes.get(node["parent_ref"])
        if node["record_type"]=="accomplishment" and parent and (parent["record_type"]=="role" or parent["section"]=="projects"):
            node["section"] = parent["section"]
            parent["children"].append(node)
            children.add(key)
        node["identity_aliases"] = sorted(set(node["identity_aliases"]))
    sections = []
    def counts(items):
        return {**{state:sum(item["state"]==state for item in items) for state in ("saved","waiting","hidden","skipped")},
                "updates_waiting":sum(item.get("update_waiting") is True for item in items)}
    section_order = resume_section_order(node["section"] for node in nodes.values())
    for key in section_order:
        label = RESUME_SECTION_LABELS[key]
        items = [node for ref,node in nodes.items() if ref not in children and node["section"]==key]
        sections.append({"key":key,"label":label,"items":items,
            "tab_visible":any(item["state"] in {"saved","waiting"} for item in items),
            "counts":counts(items),"child_counts":counts([child for item in items for child in item["children"]])})
    unplaced = [node for ref,node in nodes.items() if ref not in children and node["section"]=="unplaced"]
    non_tab = [node for ref,node in nodes.items() if ref not in children and node["section"] in {"story","contact","looking_ahead"}]
    top = [node for ref,node in nodes.items() if ref not in children and node["section"] not in {"story","contact","looking_ahead"}]
    result = {"schema_version":1,"load_state":"loaded","section_order":list(section_order),
        "sections":sections,"unplaced":unplaced,"non_tab_items":non_tab,"legacy_outcomes":legacy,"active_sources":active_sources,"draft_version":draft_version,
        "lifecycle_epoch":snapshot.get("lifecycle_epoch",0),"publication_state":"unknown",
        "counts":counts(top),"child_counts":counts([nodes[key] for key in children]),
        "child_count":len(children),"last_receipt":deepcopy(snapshot.get("last_receipt"))}
    refresh_working_set_token(owner,result)
    return result


def refresh_working_set_token(owner, working_set):
    # A once-only welcome acknowledgment is UI lifecycle, not resume content.
    body = {key:value for key,value in working_set.items() if key not in {"working_set_token", "first_arrival"}}
    working_set["working_set_token"] = sha256(_json([owner,body]).encode()).hexdigest()


def resolve_guide_references(working_set, *, evidence_refs=None, highlight_refs=()):
    """Resolve server-held references against this owner's current private tree.

    No keyword matching, copied source truth, writes or permission expansion.
    Hidden references remain stored by the caller and are only filtered here.
    Pending/absent records never supply evidence, labels or numbers.
    """
    evidence_refs = evidence_refs or {}
    if type(evidence_refs) is not dict or not isinstance(highlight_refs,(list,tuple)):
        raise ValueError("Invalid private Resume references")
    index, ambiguous = {},set()
    def collect(items, ancestor_hidden=False):
        for item in items:
            hidden = ancestor_hidden or item.get("state") == "hidden"
            visible = not hidden and item.get("origin") == "saved" and item.get("state") == "saved"
            for key in (item["item_ref"], *item.get("identity_aliases",[])):
                if key in index and index[key][0] is not None and index[key][0]["item_ref"] != item["item_ref"]:
                    ambiguous.add(key)
                index[key] = (None,False) if key in ambiguous else (item, visible)
            collect(item.get("children",[]), hidden)
    collect([*(row for section in working_set["sections"] for row in section["items"]),
        *working_set["unplaced"], *working_set["non_tab_items"]])
    needs_recheck = []

    def role_detail(role):
        values = role.get("values") or {}
        return {"role_ref":role["item_ref"], **{name:values.get(name) for name in
            ("employer_name","role_title","start_date","end_date","date_precision","current_role")}}

    def resolve(ref):
        if type(ref) is str:
            row, visible = index.get(ref,(None,False))
            if row is None or not visible or row.get("record_type") != "accomplishment":
                return None
            parent, shown = index.get(row.get("parent_ref"),(None,False))
            if parent is None or not shown or parent.get("record_type") != "role":
                return None
            text = (row.get("values") or {}).get("wording")
            if not isinstance(text,str) or not text.strip():
                return None
            return {"evidence_ref":ref,"record_ref":row["item_ref"],"text":text,**role_detail(parent)}
        if type(ref) is not dict or set(ref) != {"role_record_key","line_digest"}:
            return None
        role, visible = index.get(ref.get("role_record_key"),(None,False))
        if role is None or not visible or role.get("record_type") != "role":
            return None
        summary = (role.get("values") or {}).get("summary")
        lines = summary.splitlines() if isinstance(summary,str) else []
        matched = [line for line in lines if line.strip() and sha256(line.encode("utf-8")).hexdigest() == ref.get("line_digest")]
        if not matched:
            needs_recheck.append({"reference":deepcopy(ref),"reason":"summary_changed"})
            return None
        return {"evidence_ref":deepcopy(ref),"record_ref":None,"text":matched[0],**role_detail(role)}

    skill_evidence = {}
    for key, refs in evidence_refs.items():
        if type(key) is not str or type(refs) is not list:
            raise ValueError("Invalid skill evidence references")
        skill, visible = index.get(key,(None,False))
        resolved, seen = [],set()
        if skill is not None and visible and skill.get("record_type") == "skill":
            for ref in refs:
                identity = _json(ref)
                if identity in seen:
                    continue
                seen.add(identity)
                entry = resolve(ref)
                if entry is not None:
                    resolved.append(entry)
                if len(resolved) == 3:
                    break
        skill_evidence[key] = resolved
    highlights, seen = [],set()
    for ref in highlight_refs:
        if type(ref) is not str or ref in seen:
            continue
        seen.add(ref)
        entry = resolve(ref)
        if entry is None:
            continue
        row = index[ref][0]
        values = row.get("values") or {}
        metric = values.get("metric_value")
        if not isinstance(metric,str) or not metric.strip():
            continue
        highlights.append({**entry,"metric_value":metric,"metric_label":values.get("metric_label")})
        if len(highlights) == 4:
            break
    return {"skill_evidence":skill_evidence,"highlight_tiles":highlights,"needs_recheck":needs_recheck}


def guide_publication_state(working_set, owner_preview):
    """Use the existing owner publication authority; a failed read is not absence."""
    if (type(owner_preview) is not dict or owner_preview.get("read_state") != "current"
            or type(owner_preview.get("sharing_enabled")) is not bool):
        return "unknown"
    current = owner_preview.get("current")
    if not owner_preview["sharing_enabled"] or current is None:
        return "unpublished"
    if type(current) is not dict or type(current.get("evidence")) is not dict:
        return "unknown"
    def flattened(items):
        for item in items:
            yield item
            yield from flattened(item.get("children") or [])
    items = list(flattened([item for section in working_set["sections"] for item in section["items"]]
                          +working_set.get("unplaced",[])+working_set.get("non_tab_items",[])))
    items = [item for item in items if item["origin"]=="saved"]
    evidence = current["evidence"]
    unknown = False
    for item in items:
        published = evidence.get(item["item_ref"])
        if item.get("has_draft") or (published and item["state"]=="hidden"):
            return "changes_waiting"
        if published:
            version = item.get("saved_content_version")
            if type(version) is not int or version < 1:
                unknown = True
            elif str(version) != published.get("canonical_token"):
                return "changes_waiting"
            if published.get("access_revision") is not None:
                access = item.get("saved_access_revision")
                if type(access) is not int:
                    unknown = True
                elif access != published["access_revision"]:
                    return "changes_waiting"
        if item["origin"]=="saved" and item["state"]=="saved" and published is None:
            return "changes_waiting"
    if set(evidence)-{item["item_ref"] for item in items}:
        return "changes_waiting"
    return "unknown" if unknown else "published"
