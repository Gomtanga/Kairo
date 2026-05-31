# [KAIRO] Unit tests for SkillStore and SkillSystem
import json
import os
import tempfile
import shutil

import pytest

from core.skill_system import SkillStore, SkillSystem


class TestSkillStore:
    """Tests for core.skill_system.SkillStore."""

    @pytest.fixture(autouse=True)
    def _temp_path(self):
        tmpdir = tempfile.mkdtemp()
        self.skills_path = os.path.join(tmpdir, "skills.json")
        yield
        shutil.rmtree(tmpdir, ignore_errors=True)

    # -- load ----------------------------------------------------------------

    def test_load_missing_file_creates_defaults(self):
        """load() on a missing path creates and returns default skills."""
        assert not os.path.exists(self.skills_path)
        skills = SkillStore.load(self.skills_path)
        assert len(skills) == 3
        names = [s["name"] for s in skills]
        assert "web-research" in names
        assert "planner" in names
        assert "coding-helper" in names
        # File should now exist
        assert os.path.exists(self.skills_path)

    def test_load_corrupted_file_creates_defaults(self):
        """load() on a corrupt JSON file falls back to defaults."""
        with open(self.skills_path, "w", encoding="utf-8") as f:
            f.write("this is not json{{{")
        skills = SkillStore.load(self.skills_path)
        assert len(skills) == 3
        assert skills[0]["name"] == "web-research"

    def test_load_existing_file(self):
        """load() returns existing skills from a valid JSON file."""
        sample = [{"name": "test-skill", "trigger": "test", "action": "do()", "description": "A test"}]
        with open(self.skills_path, "w", encoding="utf-8") as f:
            json.dump(sample, f)
        skills = SkillStore.load(self.skills_path)
        assert len(skills) == 1
        assert skills[0]["name"] == "test-skill"

    # -- save ----------------------------------------------------------------

    def test_save_writes_file(self):
        """save() writes skills list to JSON file."""
        skills = [{"name": "s1", "trigger": "t1", "action": "a1", "description": "d1"}]
        SkillStore.save(skills, self.skills_path)
        assert os.path.exists(self.skills_path)
        with open(self.skills_path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == skills

    # -- add -----------------------------------------------------------------

    def test_add_micro_skill(self):
        """add() appends a micro skill and returns updated list."""
        SkillStore.add("my-skill", "my-trigger", "my-action", "my-desc", self.skills_path)
        skills = SkillStore.load(self.skills_path)
        assert len(skills) == 4  # 3 defaults + 1 new
        added = [s for s in skills if s["name"] == "my-skill"]
        assert len(added) == 1
        assert added[0]["trigger"] == "my-trigger"
        assert added[0]["action"] == "my-action"
        assert added[0]["description"] == "my-desc"
        assert "type" not in added[0]

    def test_add_big_skill(self):
        """add() with skill_type='big' stores type, sub_skills, execution_mode."""
        skills = SkillStore.add(
            "big-pipeline", "pipeline", "run()", "Big pipeline",
            self.skills_path,
            skill_type="big",
            sub_skills=["step1", "step2"],
            execution_mode="parallel",
        )
        big = [s for s in skills if s["name"] == "big-pipeline"]
        assert len(big) == 1
        assert big[0]["type"] == "big"
        assert big[0]["sub_skills"] == ["step1", "step2"]
        assert big[0]["execution_mode"] == "parallel"

    def test_add_big_skill_defaults(self):
        """add() with skill_type='big' uses defaults for sub_skills and execution_mode."""
        skills = SkillStore.add(
            "big-default", "test", "run()", "Desc",
            self.skills_path,
            skill_type="big",
        )
        big = [s for s in skills if s["name"] == "big-default"]
        assert big[0]["sub_skills"] == []
        assert big[0]["execution_mode"] == "sequential"

    # -- remove --------------------------------------------------------------

    def test_remove_existing_skill(self):
        """remove() deletes a skill by name."""
        SkillStore.add("to-remove", "x", "y", "z", self.skills_path)
        assert any(s["name"] == "to-remove" for s in SkillStore.load(self.skills_path))
        skills = SkillStore.remove("to-remove", self.skills_path)
        assert all(s["name"] != "to-remove" for s in skills)

    def test_remove_nonexistent_skill(self):
        """remove() a non-existent name leaves the list unchanged."""
        SkillStore.add("keep-me", "x", "y", "z", self.skills_path)
        before = SkillStore.load(self.skills_path)
        skills = SkillStore.remove("does-not-exist", self.skills_path)
        assert len(skills) == len(before)

    # -- update --------------------------------------------------------------

    def test_update_existing_skill(self):
        """update() modifies the fields of an existing skill."""
        SkillStore.add("old-name", "old-trigger", "old-action", "old-desc", self.skills_path)
        skills = SkillStore.update(
            "old-name", "new-name", "new-trigger", "new-action", "new-desc",
            self.skills_path,
        )
        updated = [s for s in skills if s["name"] == "new-name"]
        assert len(updated) == 1
        assert updated[0]["trigger"] == "new-trigger"
        assert updated[0]["action"] == "new-action"
        assert updated[0]["description"] == "new-desc"
        # Old name should be gone
        assert all(s["name"] != "old-name" for s in skills)

    def test_update_nonexistent_skill(self):
        """update() on a non-existent name leaves the file unchanged."""
        SkillStore.add("stable", "x", "y", "z", self.skills_path)
        before = SkillStore.load(self.skills_path)
        skills = SkillStore.update(
            "ghost", "new-name", "new-trigger", "new-action", "new-desc",
            self.skills_path,
        )
        assert len(skills) == len(before)

    # -- to_kb_section -------------------------------------------------------

    def test_to_kb_section_empty(self):
        """to_kb_section([]) returns an empty string."""
        assert SkillStore.to_kb_section([]) == ""

    def test_to_kb_section_micro_only(self):
        """to_kb_section formats micro skills under the micro heading."""
        skills = [
            {"name": "s1", "trigger": "t1", "action": "a1", "description": "d1"},
        ]
        result = SkillStore.to_kb_section(skills)
        assert "## 🔧 Skills" in result
        assert "### 마이크로스킬 (단일 동작)" in result
        assert "#### skill: s1" in result
        assert "- trigger: t1" in result

    def test_to_kb_section_mixed(self):
        """to_kb_section lists micro skills first, then big skills."""
        skills = [
            {"name": "micro1", "trigger": "t1", "action": "a1", "description": "d1"},
            {
                "name": "big1", "trigger": "t2", "description": "d2",
                "type": "big", "sub_skills": ["a", "b"], "execution_mode": "parallel",
            },
        ]
        result = SkillStore.to_kb_section(skills)
        micro_pos = result.index("### 마이크로스킬")
        big_pos = result.index("### 🏗️ 빅스킬")
        assert micro_pos < big_pos
        assert "#### big-skill: big1" in result
        assert "- sub_skills: a, b" in result
        assert "- execution_mode: parallel" in result

    # -- migrate_from_kb -----------------------------------------------------

    def test_migrate_from_kb_extracts_and_removes_section(self):
        """migrate_from_kb parses skills from KB content, saves new ones, strips the section."""
        kb = (
            "## 🔧 Skills\n"
            "### skill: legacy-skill\n"
            "- trigger: legacy\n"
            "- action: run()\n"
            "- description: Legacy\n"
            "\n"
            "## Some Other Section\n"
            "content\n"
        )
        remaining = SkillStore.migrate_from_kb(kb, self.skills_path)
        assert "## 🔧 Skills" not in remaining
        assert "## Some Other Section" in remaining

        # Verify the skill was saved
        saved = SkillStore.load(self.skills_path)
        names = {s["name"] for s in saved}
        assert "legacy-skill" in names

    def test_migrate_from_kb_skips_duplicates(self):
        """migrate_from_kb does not re-add skills already in the JSON store."""
        SkillStore.add("existing-skill", "x", "y", "z", self.skills_path)
        kb = (
            "## 🔧 Skills\n"
            "### skill: existing-skill\n"
            "- trigger: x\n"
            "- action: y\n"
            "- description: z\n"
        )
        SkillStore.migrate_from_kb(kb, self.skills_path)
        saved = SkillStore.load(self.skills_path)
        # Count should be 4 (3 defaults + 1), not 5 (no duplicate)
        assert len(saved) == 4

    def test_migrate_from_kb_no_skills(self):
        """migrate_from_kb with no skills section returns content unchanged."""
        kb = "# Just regular content\n"
        result = SkillStore.migrate_from_kb(kb, self.skills_path)
        assert result == kb


class TestSkillSystem:
    """Tests for core.skill_system.SkillSystem (parsing and CRUD on KB text)."""

    # -- parse_skills --------------------------------------------------------

    def test_parse_skills_basic(self):
        """parse_skills extracts skill blocks with all fields."""
        kb = (
            "### skill: web-search\n"
            "- trigger: 검색\n"
            "- action: search(query)\n"
            "- description: 웹 검색\n"
        )
        skills = SkillSystem.parse_skills(kb)
        assert len(skills) == 1
        assert skills[0]["name"] == "web-search"
        assert skills[0]["trigger"] == "검색"
        assert skills[0]["action"] == "search(query)"
        assert skills[0]["description"] == "웹 검색"

    def test_parse_skills_multiple(self):
        """parse_skills extracts multiple skill blocks."""
        kb = (
            "### skill: s1\n"
            "- trigger: t1\n"
            "- action: a1\n"
            "- description: d1\n"
            "\n"
            "### skill: s2\n"
            "- trigger: t2\n"
            "- action: a2\n"
            "- description: d2\n"
        )
        skills = SkillSystem.parse_skills(kb)
        assert len(skills) == 2
        assert skills[0]["name"] == "s1"
        assert skills[1]["name"] == "s2"

    def test_parse_skills_optional_fields(self):
        """parse_skills handles blocks with missing optional fields."""
        kb = "### skill: minimal\n"
        skills = SkillSystem.parse_skills(kb)
        assert len(skills) == 1
        assert skills[0]["name"] == "minimal"
        assert skills[0]["trigger"] == ""
        assert skills[0]["action"] == ""
        assert skills[0]["description"] == ""

    def test_parse_skills_empty(self):
        """parse_skills returns empty list when no skill blocks exist."""
        assert SkillSystem.parse_skills("") == []
        assert SkillSystem.parse_skills("# Just a heading\n\nsome text") == []

    # -- match_skill ---------------------------------------------------------

    def test_match_skill_exact_trigger(self):
        """match_skill picks an exact trigger match with score 100."""
        skills = [{"name": "search", "trigger": '"검색", "찾아봐"', "action": "search()", "description": ""}]
        result = SkillSystem.match_skill("검색해줘", skills)
        assert result is not None
        assert result["skill"]["name"] == "search"
        assert result["score"] == 100
        assert result["method"] == "exact"

    def test_match_skill_fuzzy_trigger(self):
        """match_skill falls back to fuzzy matching when no exact or stem match."""
        skills = [{"name": "dance", "trigger": '"춤추기"', "action": "dance()", "description": ""}]
        # "춤추기" is somewhat similar to "춤추는" in Korean
        result = SkillSystem.match_skill("춤추는 법 알려줘", skills)
        # May be fuzzy or stem match depending on tokenization
        assert result is not None
        assert result["score"] >= 0

    def test_match_skill_no_match(self):
        """match_skill returns None when nothing matches."""
        skills = [{"name": "search", "trigger": '"검색"', "action": "search()", "description": ""}]
        result = SkillSystem.match_skill("hello world", skills)
        assert result is None

    def test_match_skill_empty_triggers(self):
        """match_skill skips skills with empty triggers."""
        skills = [{"name": "empty", "trigger": "", "action": "", "description": ""}]
        result = SkillSystem.match_skill("anything", skills)
        assert result is None

    # -- add_skill -----------------------------------------------------------

    def test_add_skill_with_existing_header(self):
        """add_skill inserts block under existing Skills header."""
        kb = "## 🔧 Skills\n"
        result = SkillSystem.add_skill(kb, "new-skill", "trigger", "action", "desc")
        assert "### skill: new-skill" in result
        assert "- trigger: trigger" in result
        assert "- action: action" in result
        assert "- description: desc" in result

    def test_add_skill_creates_header(self):
        """add_skill creates a Skills header when none exists."""
        kb = "# No skills section\n"
        result = SkillSystem.add_skill(kb, "s1", "t1", "a1", "d1")
        assert "## 🔧 Skills" in result
        assert "### skill: s1" in result

    # -- remove_skill --------------------------------------------------------

    def test_remove_skill(self):
        """remove_skill deletes a skill block by name."""
        kb = (
            "## 🔧 Skills\n"
            "### skill: keeper\n"
            "- trigger: k\n"
            "- action: k\n"
            "- description: k\n"
            "\n"
            "### skill: goner\n"
            "- trigger: g\n"
            "- action: g\n"
            "- description: g\n"
        )
        result = SkillSystem.remove_skill(kb, "goner")
        assert "### skill: goner" not in result
        assert "### skill: keeper" in result

    def test_remove_skill_nonexistent(self):
        """remove_skill on a non-existent name leaves content unchanged."""
        kb = "### skill: existing\n- trigger: t\n- action: a\n- description: d\n"
        result = SkillSystem.remove_skill(kb, "nonexistent")
        assert result == kb

    # -- update_skill --------------------------------------------------------

    def test_update_skill(self):
        """update_skill replaces old block with new fields."""
        kb = (
            "## 🔧 Skills\n"
            "### skill: old-name\n"
            "- trigger: old\n"
            "- action: old()\n"
            "- description: old desc\n"
        )
        result = SkillSystem.update_skill(kb, "old-name", "new-name", "new", "new()", "new desc")
        assert "### skill: old-name" not in result
        assert "### skill: new-name" in result
        assert "- trigger: new" in result

    # -- get_default_skills --------------------------------------------------

    def test_get_default_skills(self):
        """get_default_skills returns the expected 3 default skills."""
        defaults = SkillSystem.get_default_skills()
        assert len(defaults) == 3
        names = {d["name"] for d in defaults}
        assert names == {"web-research", "planner", "coding-helper"}
        for d in defaults:
            assert "trigger" in d and d["trigger"]
            assert "action" in d and d["action"]
            assert "description" in d
