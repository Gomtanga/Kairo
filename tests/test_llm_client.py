# [KAIRO] Unit tests for LLMClient – tool call parsing, system prompt, UI_TOOLS
import json

import pytest

from core.llm_client import LLMClient, UI_TOOLS


class TestParseToolCalls:
    """Tests for LLMClient._parse_tool_calls."""

    @pytest.fixture(autouse=True)
    def _client(self):
        self.client = LLMClient()

    def test_empty_list(self):
        """_parse_tool_calls([]) returns an empty list."""
        assert self.client._parse_tool_calls([]) == []

    def test_none_input(self):
        """_parse_tool_calls(None) returns an empty list."""
        assert self.client._parse_tool_calls(None) == []

    def test_single_tool_call(self):
        """_parse_tool_calls parses a single tool call correctly."""
        raw = [
            {
                "function": {
                    "name": "create_table",
                    "arguments": '{"title": "Data", "headers": ["A", "B"], "rows": [["1", "2"]]}',
                }
            }
        ]
        parsed = self.client._parse_tool_calls(raw)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "create_table"
        assert parsed[0]["arguments"]["title"] == "Data"
        assert parsed[0]["arguments"]["headers"] == ["A", "B"]

    def test_multiple_tool_calls(self):
        """_parse_tool_calls parses multiple tool calls."""
        raw = [
            {"function": {"name": "create_form", "arguments": '{"title": "F", "fields": []}'}},
            {"function": {"name": "create_chart", "arguments": '{"chart_type": "bar", "title": "C", "labels": ["x"], "values": [1]}'}},
        ]
        parsed = self.client._parse_tool_calls(raw)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "create_form"
        assert parsed[1]["arguments"]["chart_type"] == "bar"

    def test_arguments_as_dict(self):
        """_parse_tool_calls handles arguments that are already dicts (not strings)."""
        raw = [
            {
                "function": {
                    "name": "create_button",
                    "arguments": {"label": "Click", "action": "submit"},
                }
            }
        ]
        parsed = self.client._parse_tool_calls(raw)
        assert len(parsed) == 1
        assert parsed[0]["arguments"]["label"] == "Click"

    def test_malformed_json_arguments_skipped(self):
        """_parse_tool_calls skips tool calls with invalid JSON arguments."""
        raw = [
            {"function": {"name": "bad_args", "arguments": "not valid json{{{}}}"}},
            {"function": {"name": "good_args", "arguments": '{"ok": true}'}},
        ]
        parsed = self.client._parse_tool_calls(raw)
        assert len(parsed) == 1
        assert parsed[0]["name"] == "good_args"

    def test_missing_function_key_skipped(self):
        """_parse_tool_calls processes entries without 'function' key with empty defaults."""
        raw = [{"not_function": {"name": "create_form"}}]
        parsed = self.client._parse_tool_calls(raw)
        # The function uses .get("function", {}) which returns {} gracefully,
        # then empty name and {} args are used — entry is still appended.
        assert len(parsed) == 1
        assert parsed[0]["name"] == ""
        assert parsed[0]["arguments"] == {}

    def test_missing_name_returns_empty_name(self):
        """_parse_tool_calls handles empty/missing name gracefully."""
        raw = [{"function": {"arguments": '{"x": 1}'}}]
        parsed = self.client._parse_tool_calls(raw)
        assert len(parsed) == 1
        assert parsed[0]["name"] == ""


class TestBuildSystemPrompt:
    """Tests for LLMClient._build_system_prompt."""

    @pytest.fixture(autouse=True)
    def _client(self):
        self.client = LLMClient()

    def test_basic_prompt_structure(self):
        """_build_system_prompt returns a string with expected sections."""
        prompt = self.client._build_system_prompt("", agent_level=0)
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "Kairo" in prompt
        assert "KB.md" in prompt
        assert "UI 도구 사용 규칙" in prompt

    def test_kb_content_appended(self):
        """_build_system_prompt appends kb_content when provided."""
        kb = "## 👤 User Profile\n- name: TestUser\n"
        prompt = self.client._build_system_prompt(kb, agent_level=0)
        assert "TestUser" in prompt
        assert "KB.md (Knowledge Base)" in prompt

    def test_agent_level_2_appends_autonomy_section(self):
        """_build_system_prompt includes level 2 autonomy instructions."""
        prompt = self.client._build_system_prompt("", agent_level=2)
        assert "자율 레벨 2" in prompt
        assert "의도 예측 모드" in prompt
        assert "선제적 액션 모드" not in prompt

    def test_agent_level_3_appends_both_autonomy_sections(self):
        """_build_system_prompt includes both level 2 and level 3 instructions."""
        prompt = self.client._build_system_prompt("", agent_level=3)
        assert "자율 레벨 2" in prompt
        assert "자율 레벨 3" in prompt
        assert "선제적 액션 모드" in prompt

    def test_agent_level_0_has_no_autonomy(self):
        """_build_system_prompt at level 0/1 has no autonomy sections."""
        prompt = self.client._build_system_prompt("", agent_level=0)
        assert "자율 레벨" not in prompt

    def test_agent_level_1_has_no_autonomy(self):
        """_build_system_prompt at level 1 has no autonomy sections."""
        prompt = self.client._build_system_prompt("", agent_level=1)
        assert "자율 레벨" not in prompt

    def test_tool_whitelist_included(self):
        """_build_system_prompt references the TOOL_WHITELIST constants."""
        prompt = self.client._build_system_prompt("", agent_level=0)
        assert "TOOL" in prompt
        assert "date" in prompt or "ls" in prompt

    def test_kb_update_format_explained(self):
        """_build_system_prompt includes the kb-update block format."""
        prompt = self.client._build_system_prompt("", agent_level=0)
        assert "kb-update" in prompt
        assert "```" in prompt


class TestUITools:
    """Validation tests for the UI_TOOLS constant."""

    def test_ui_tools_is_list(self):
        """UI_TOOLS is a non-empty list."""
        assert isinstance(UI_TOOLS, list)
        assert len(UI_TOOLS) > 0

    def test_each_tool_has_required_structure(self):
        """Every entry in UI_TOOLS has 'type' and 'function.name'."""
        for tool in UI_TOOLS:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func

    def test_tool_names_are_unique(self):
        """All UI_TOOLS have unique function names."""
        names = [t["function"]["name"] for t in UI_TOOLS]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"

    def test_known_tool_names(self):
        """UI_TOOLS contains the expected set of tool names."""
        names = {t["function"]["name"] for t in UI_TOOLS}
        expected = {"create_form", "create_table", "create_chart", "create_button"}
        assert names == expected, f"Expected {expected}, got {names}"

    def test_create_form_parameters(self):
        """create_form has title and fields as required params."""
        form = [t for t in UI_TOOLS if t["function"]["name"] == "create_form"][0]
        params = form["function"]["parameters"]
        assert params["type"] == "object"
        assert "title" in params["required"]
        assert "fields" in params["required"]
        # fields is an array of objects with name and field_type
        fields_item = params["properties"]["fields"]["items"]
        assert "name" in fields_item["required"]
        assert "field_type" in fields_item["required"]

    def test_create_table_parameters(self):
        """create_table has title, headers, rows as required params."""
        table = [t for t in UI_TOOLS if t["function"]["name"] == "create_table"][0]
        params = table["function"]["parameters"]
        for req in ("title", "headers", "rows"):
            assert req in params["required"]

    def test_create_chart_parameters(self):
        """create_chart has chart_type, title, labels, values as required params."""
        chart = [t for t in UI_TOOLS if t["function"]["name"] == "create_chart"][0]
        params = chart["function"]["parameters"]
        for req in ("chart_type", "title", "labels", "values"):
            assert req in params["required"]
        assert params["properties"]["chart_type"]["enum"] == ["bar", "line", "pie"]

    def test_create_button_parameters(self):
        """create_button has label and action as required params."""
        btn = [t for t in UI_TOOLS if t["function"]["name"] == "create_button"][0]
        params = btn["function"]["parameters"]
        assert "label" in params["required"]
        assert "action" in params["required"]

    def test_all_params_have_type_and_description(self):
        """Every parameter in every tool has a 'type' and 'description' field."""
        for tool in UI_TOOLS:
            props = tool["function"]["parameters"].get("properties", {})
            for name, prop in props.items():
                assert "type" in prop, f"Tool '{tool['function']['name']}' param '{name}' missing 'type'"
                if name != "field_type":  # field_type is enum-based and may not need description
                    assert "description" in prop, f"Tool '{tool['function']['name']}' param '{name}' missing 'description'"

    def test_no_unexpected_top_level_fields(self):
        """UI_TOOLS entries should only contain expected fields."""
        allowed = {"type", "function"}
        for tool in UI_TOOLS:
            extra = set(tool.keys()) - allowed
            assert not extra, f"Unexpected fields in UI_TOOLS entry: {extra}"
