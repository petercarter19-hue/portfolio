"""Focused static contracts for the bounded Community secondary-state tranche."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CommunitySecondaryStateContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = (ROOT / "templates" / "community_feed.html").read_text(encoding="utf-8")
        cls.script = (ROOT / "static" / "js" / "community-v1.js").read_text(encoding="utf-8")
        cls.preview = (ROOT / "scripts" / "preview_community_secondary_states.py").read_text(encoding="utf-8")

    def test_conversation_keeps_full_context_and_compact_emoji_response(self):
        self.assertNotIn("data-response-dialog", self.template)
        self.assertIn("function conversationPostControls(post)", self.script)
        self.assertIn("primaryRespondControl(post, 'conversation')", self.script)
        self.assertIn("function mergeSelectedConversationContext(post)", self.script)
        self.assertIn("function selectedConversationContext(selected)", self.script)
        self.assertIn("appendContributionTree(conversationBody, post.contributions)", self.script)
        self.assertIn("node.dataset.conversationFocus", self.script)
        self.assertIn("focusNode.scrollIntoView({block: 'center'})", self.script)
        self.assertIn("card.appendChild(el('h2', 'cv1-card-title', conversationCopy.title))", self.script)
        self.assertIn("if (event.target === conversation)", self.script)
        header_actions = self.script[
            self.script.index("function renderConversationHeaderActions"):
            self.script.index("function mergeSelectedConversationContext")
        ]
        self.assertNotIn("postOwnerControls", header_actions)

    def test_reply_composer_preserves_private_drafts_and_approved_voice_tool(self):
        for control in (
            "data-reply-attachment-input",
            "data-reply-photo-input",
            "data-reply-send",
            "data-reply-voice",
            "data-video-unavailable",
            "data-public-audio-unavailable",
        ):
            self.assertIn(control, self.template)
        self.assertIn("function replyDraftStorageKey(postKey, parentKey)", self.script)
        self.assertIn("draftKey + ':reply-draft:' + postKey", self.script)
        self.assertIn("Math.min(input.scrollHeight, 168)", self.script)
        self.assertIn("state.replyParentKey = item.key", self.script)
        self.assertIn("setupReplyVoiceController", self.script)
        self.assertIn("context: 'contribution'", self.script)
        self.assertIn("maxLength: 2000", self.script)
        self.assertIn("Public audio attachments are not available in this owner pilot.", self.script)

    def test_original_post_requires_explicit_public_confirmation_before_post(self):
        self.assertIn("data-public-confirmation", self.template)
        self.assertIn("Review public post", self.template)
        self.assertIn("Publish publicly", self.template)
        self.assertIn("function openPublicConfirmation()", self.script)
        self.assertIn("function confirmPublicPublication()", self.script)
        publish = self.script[self.script.index("function publish(event)"):self.script.index("function confirmPublicPublication()")]
        self.assertIn("openPublicConfirmation();", publish)
        confirm = self.script[self.script.index("function confirmPublicPublication()"):self.script.index("function tombstoneNode")]
        self.assertIn("submitComposerMutation();", confirm)

    def test_secondary_preview_is_fixture_only_and_does_not_touch_persistence(self):
        self.assertIn("intentionally separate from the approved primary Feed harness", self.preview)
        self.assertIn("community_preview=True", self.preview)
        self.assertIn("FOCUSED_CONTRIBUTION_KEY", self.preview)
        self.assertIn("Public publishing is intentionally disabled", self.preview)
        self.assertIn("File upload is intentionally not represented", self.preview)
        self.assertNotIn("DatabaseService", self.preview)
        self.assertNotIn("from services.", self.preview)


if __name__ == "__main__":
    unittest.main()
