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


if __name__ == "__main__":
    unittest.main()
