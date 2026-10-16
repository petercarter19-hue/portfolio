"""Pure B3b conversion rules: supported moves, the D6a descriptor and reference reconciliation."""
import unittest

from services.resume_guide_turns import (
    CONVERSION_DESCRIPTOR_KEYS, conversion_descriptor, conversion_supported, conversion_token,
    destination_needs_parent, reconcile_references, reference_digest,
)


class ConversionRuleTests(unittest.TestCase):
    def test_only_the_b3b_moves_are_supported(self):
        for pair in (("skill", "accomplishment"), ("skill", "project"), ("accomplishment", "skill"), ("project", "skill")):
            self.assertTrue(conversion_supported(*pair), pair)
        for pair in (("education", "credential"), ("accomplishment", "project"), ("skill", "skill"), ("role", "skill")):
            self.assertFalse(conversion_supported(*pair), pair)
        self.assertTrue(destination_needs_parent("accomplishment"))
        self.assertFalse(destination_needs_parent("project"))

    def test_descriptor_has_exactly_the_d6a_keys_and_the_publisher_refuses_it(self):
        from services.resume_publication_service import (
            CONVERSION_DESCRIPTOR_KEYS as PUBLISHER_KEYS, TYPE_TRANSITION_UNAVAILABLE, conversion_publication_blocker)
        descriptor = conversion_descriptor(base_record_type="skill", destination_record_type="project",
            destination_parent_ref=None, base_content_token="token-1", base_access_revision=2, operation_ref="op:x:0")
        self.assertEqual(set(descriptor), set(CONVERSION_DESCRIPTOR_KEYS))
        self.assertEqual(set(descriptor), set(PUBLISHER_KEYS))
        self.assertEqual(conversion_publication_blocker({"conversion": descriptor}), TYPE_TRANSITION_UNAVAILABLE)

    def test_token_binds_the_reviewed_destination(self):
        base = {"record_key": "r", "record_type": "skill"}
        first = conversion_token("o", "k", "i", base, {"record_type": "project", "values": {"a": 1}}, [])
        self.assertNotEqual(first, conversion_token("o", "k", "i", base, {"record_type": "project", "values": {"a": 2}}, []))
        self.assertEqual(first, conversion_token("o", "k", "i", base, {"record_type": "project", "values": {"a": 1}}, []))


class ReferenceReconciliationTests(unittest.TestCase):
    def affected(self, refs, kind="skill", container="skill-1"):
        return [{"kind": kind, "container_ref": container, "references": refs, "before_digest": reference_digest(refs)}]

    def entry(self, refs, final, kind="skill", container="skill-1", digest=None):
        return {"kind": kind, "container_ref": container, "before_digest": digest or reference_digest(refs), "references": final}

    def test_every_affected_container_needs_one_reviewed_final_list(self):
        affected = self.affected(["b1", "b2"])
        with self.assertRaisesRegex(ValueError, "reconciliation_required"):
            reconcile_references(affected, [], invalid_refs={})
        final = reconcile_references(affected, [self.entry(["b1", "b2"], ["b1"])], invalid_refs={})
        self.assertEqual(final, {("skill", "skill-1"): ["b1"]})

    def test_invalid_added_reordered_or_stale_choices_refuse(self):
        affected = self.affected(["b1", "b2"])
        invalid = {("skill", "skill-1"): {"b2"}}
        for final in (["b2"], ["b3"], ["b2", "b1"], ["b1", "b1"]):
            with self.subTest(final=final), self.assertRaisesRegex(ValueError, "reconciliation_required"):
                reconcile_references(affected, [self.entry(["b1", "b2"], final)], invalid_refs=invalid)
        with self.assertRaisesRegex(ValueError, "changed"):
            reconcile_references(affected, [self.entry(["b1", "b2"], ["b1"], digest="0" * 64)], invalid_refs={})


class TileNumberTests(unittest.TestCase):
    """B3t: numbers are read from a bullet's own current wording, deterministically and without AI."""

    def test_tokens_cover_currency_grouping_decimals_scale_and_suffixes(self):
        from services.resume_guide_turns import metric_numbers
        self.assertEqual(metric_numbers("Led 30+ engineers on 9 redesigns worth $19.2M, 35% faster and 2.5x cheaper."),
                         ["30+", "9", "$19.2M", "35%", "2.5x"])
        self.assertEqual(metric_numbers("Moved 1,200 records and EUR-free €4.5bn, £300k, 12 sites in 2019."),
                         ["1,200", "€4.5bn", "£300k", "12", "2019"])
        self.assertEqual(metric_numbers("No numbers here."), [])
        self.assertEqual(metric_numbers(None), [])

    def test_index_zero_is_the_stored_metric_and_later_indexes_skip_it_once(self):
        from services.resume_guide_turns import nth_metric
        wording = "Led 30+ engineers on 9 redesigns worth $19.2M."
        self.assertEqual(nth_metric(wording, "30+", 0), "30+")
        self.assertEqual(nth_metric(wording, "30+", 1), "9")
        self.assertEqual(nth_metric(wording, "30+", 2), "$19.2M")
        self.assertIsNone(nth_metric(wording, "30+", 3))
        self.assertEqual(nth_metric(wording, "a stored figure not in the words", 1), "30+")
        self.assertIsNone(nth_metric(wording, None, 0))
        self.assertEqual(nth_metric("12 of 12 checks passed.", "12", 1), "12", "Only the first equal token is skipped")

    def test_entries_normalize_to_the_frozen_shape(self):
        from services.resume_guide_turns import highlight_entry, tile_key
        ref = "8b6a5c9e-0d4f-4e63-9a1c-7e2b5d3f1a90"
        self.assertEqual(highlight_entry(ref), ref)
        self.assertEqual(highlight_entry({"item_ref": ref, "metric_index": 0}), ref, "Index 0 without a caption stays a plain key")
        self.assertEqual(highlight_entry({"item_ref": ref, "metric_index": 0, "caption": "  Engineers led  "}),
                         {"item_ref": ref, "metric_index": 0, "caption": "Engineers led"})
        self.assertEqual(highlight_entry({"item_ref": ref, "metric_index": 2}), {"item_ref": ref, "metric_index": 2})
        for bad in ({"item_ref": ref, "metric_index": -1}, {"item_ref": ref, "metric_index": True},
                    {"item_ref": ref, "metric_index": 1, "metric_text": "$19.2M"}, {"item_ref": ref, "caption": "x"},
                    {"item_ref": ref, "metric_index": 1, "caption": "   "},
                    {"item_ref": ref, "metric_index": 1, "caption": "x" * 81}, {"item_ref": ref, "metric_index": 1, "other": 1}, 7):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                highlight_entry(bad)
        self.assertEqual(tile_key(ref), (ref, 0))
        self.assertEqual(tile_key({"item_ref": ref, "metric_index": 2, "metric_text": "$19.2M"}), (ref, 2))


if __name__ == "__main__":
    unittest.main()
