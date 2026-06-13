"""CapCut Draft project manager."""
import json
import os
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class DraftInfo:
    """Basic info about a CapCut draft project."""
    name: str
    path: str
    draft_content_path: str
    has_audio: bool = False
    has_video: bool = False


class DraftManager:
    """Manages CapCut draft projects: discovery, reading, and writing."""

    def __init__(self, drafts_root: str):
        """
        Args:
            drafts_root: Root directory containing CapCut draft folders
        """
        self.drafts_root = drafts_root

    def discover_drafts(self) -> List[DraftInfo]:
        """Scan drafts_root for valid CapCut projects.

        Returns:
            List of discovered draft projects
        """
        drafts = []

        if not os.path.isdir(self.drafts_root):
            return drafts

        for name in sorted(os.listdir(self.drafts_root)):
            folder = os.path.join(self.drafts_root, name)
            content_file = os.path.join(folder, "draft_content.json")

            if os.path.isfile(content_file):
                drafts.append(DraftInfo(
                    name=name,
                    path=folder,
                    draft_content_path=content_file,
                ))

        return drafts

    def load_draft(self, draft: DraftInfo) -> dict:
        """Load and parse draft_content.json.

        Args:
            draft: DraftInfo to load

        Returns:
            Parsed JSON content as dict
        """
        with open(draft.draft_content_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_draft(self, draft: DraftInfo, content: dict):
        """Save modified content back to draft_content.json.

        Creates a backup before overwriting.

        Args:
            draft: Target draft
            content: Modified content dict
        """
        # Backup original
        backup_path = draft.draft_content_path + ".bak"
        if os.path.exists(draft.draft_content_path):
            import shutil
            shutil.copy2(draft.draft_content_path, backup_path)

        with open(draft.draft_content_path, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, separators=(',', ':'))

    def get_materials(self, content: dict) -> List[dict]:
        """Extract material (media) entries from draft content.

        Args:
            content: Parsed draft_content.json

        Returns:
            List of material entries
        """
        materials = content.get("materials", {})
        videos = materials.get("videos", [])
        audios = materials.get("audios", [])
        return videos + audios

    def get_tracks(self, content: dict) -> List[dict]:
        """Extract timeline tracks from draft content.

        Args:
            content: Parsed draft_content.json

        Returns:
            List of track entries
        """
        return content.get("tracks", [])
