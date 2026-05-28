import pytest
from core.knowledge_graph import KnowledgeGraph


class TestKnowledgeGraph:

    def test_add_edge(self):
        """Add an edge, verify it appears in content with correct fields."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        result = KnowledgeGraph.add_edge(content, "Python", "ML", "related")
        assert "### Edge: Python → ML" in result
        assert "- source: Python" in result
        assert "- target: ML" in result
        assert "- type: related" in result
        assert "- discovered:" in result

    def test_add_edge_no_duplicate(self):
        """Add same edge twice, verify content unchanged on second call."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        r1 = KnowledgeGraph.add_edge(content, "A", "B", "related")
        r2 = KnowledgeGraph.add_edge(r1, "A", "B", "related")
        assert r1 == r2

    def test_add_edge_new_section(self):
        """Add edge when no graph section exists yet — header should be created."""
        content = "# Some KB content\n"
        result = KnowledgeGraph.add_edge(content, "X", "Y", "depends")
        assert KnowledgeGraph.GRAPH_SECTION_HEADER in result
        assert "### Edge: X → Y" in result
        assert "- source: X" in result
        assert "- target: Y" in result
        assert "- type: depends" in result

    def test_remove_edge(self):
        """Add edge then remove it, verify it's gone."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        content = KnowledgeGraph.add_edge(content, "Python", "ML", "related")
        assert "### Edge: Python → ML" in content
        result = KnowledgeGraph.remove_edge(content, "Python → ML")
        assert "### Edge: Python → ML" not in result
        # Header should remain
        assert KnowledgeGraph.GRAPH_SECTION_HEADER in result

    def test_remove_edge_preserves_other_edges(self):
        """Remove one edge should not affect another edge in the same section."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        content = KnowledgeGraph.add_edge(content, "A", "B", "related")
        content = KnowledgeGraph.add_edge(content, "C", "D", "related")
        result = KnowledgeGraph.remove_edge(content, "A → B")
        assert "### Edge: A → B" not in result
        assert "### Edge: C → D" in result

    def test_remove_nonexistent_edge(self):
        """Remove non-existent edge, content unchanged."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        content = KnowledgeGraph.add_edge(content, "A", "B", "related")
        result = KnowledgeGraph.remove_edge(content, "NONEXISTENT")
        assert result == content

    def test_parse_edges(self):
        """Add 2 edges, parse them, verify 2 edges returned with correct fields."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        content = KnowledgeGraph.add_edge(content, "Python", "ML", "related")
        content = KnowledgeGraph.add_edge(content, "React", "TypeScript", "depends")
        edges = KnowledgeGraph.parse_edges(content)
        assert len(edges) == 2

        names = {e["name"] for e in edges}
        assert "Python → ML" in names
        assert "React → TypeScript" in names

        # Verify fields on each parsed edge
        for e in edges:
            assert "source" in e
            assert "target" in e
            assert "type" in e
            assert "discovered" in e

        # Check specific edge content
        edge_map = {e["name"]: e for e in edges}
        assert edge_map["Python → ML"]["source"] == "Python"
        assert edge_map["Python → ML"]["target"] == "ML"
        assert edge_map["Python → ML"]["type"] == "related"
        assert edge_map["React → TypeScript"]["source"] == "React"
        assert edge_map["React → TypeScript"]["target"] == "TypeScript"
        assert edge_map["React → TypeScript"]["type"] == "depends"

    def test_parse_edges_empty_section(self):
        """Parse edges when graph section has no edges."""
        content = f"{KnowledgeGraph.GRAPH_SECTION_HEADER}\n"
        edges = KnowledgeGraph.parse_edges(content)
        assert edges == []

    def test_parse_edges_no_section(self):
        """Parse edges when graph section does not exist at all."""
        content = "# Just regular content\n"
        edges = KnowledgeGraph.parse_edges(content)
        assert edges == []

    def test_format_edges_for_display(self):
        """Verify formatted display strings look correct."""
        edges = [
            {"name": "Python → ML", "source": "Python", "target": "ML",
             "type": "related", "discovered": "2025-05-28"},
        ]
        formatted = KnowledgeGraph.format_edges_for_display(edges)
        assert len(formatted) == 1
        assert "Python" in formatted[0]
        assert "ML" in formatted[0]
        assert "related" in formatted[0]
        assert "2025-05-28" in formatted[0]
