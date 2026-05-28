# [KAIRO] Knowledge Graph module - manages knowledge relationships in KB.md
import re
from datetime import datetime
from typing import Optional


class KnowledgeGraph:

    GRAPH_SECTION_HEADER = "## 🧩 Knowledge Graph (자동 발견)"

    @staticmethod
    def parse_edges(kb_content: str) -> list[dict]:
        edges = []
        in_graph_section = False
        current_edge = {}

        for line in kb_content.split("\n"):
            stripped = line.strip()

            if stripped == KnowledgeGraph.GRAPH_SECTION_HEADER:
                in_graph_section = True
                continue

            if in_graph_section:
                if stripped.startswith("## ") and stripped != KnowledgeGraph.GRAPH_SECTION_HEADER:
                    if current_edge:
                        edges.append(current_edge)
                    break

                if stripped.startswith("### Edge:"):
                    if current_edge:
                        edges.append(current_edge)
                    edge_name = stripped.replace("### Edge:", "").strip()
                    current_edge = {"name": edge_name}
                elif current_edge and stripped.startswith("- "):
                    match = re.match(r"- (\w+):\s*(.+)", stripped)
                    if match:
                        key, value = match.group(1), match.group(2).strip()
                        current_edge[key] = value

        if current_edge:
            edges.append(current_edge)

        return edges

    @staticmethod
    def add_edge(kb_content: str, source: str, target: str, edge_type: str, edge_name: Optional[str] = None) -> str:
        if not edge_name:
            edge_name = f"{source} → {target}"
        # [KAIRO] dedup check
        if f"### Edge: {edge_name}" in kb_content:
            return kb_content

        timestamp = datetime.now().strftime("%Y-%m-%d")
        edge_block = (
            f"\n### Edge: {edge_name}\n"
            f"- source: {source}\n"
            f"- target: {target}\n"
            f"- type: {edge_type}\n"
            f"- discovered: {timestamp}\n"
        )

        graph_header = KnowledgeGraph.GRAPH_SECTION_HEADER
        if graph_header in kb_content:
            kb_content = kb_content.replace(
                graph_header,
                graph_header + edge_block,
            )
        else:
            kb_content += f"\n{graph_header}\n{edge_block}\n"

        return kb_content

    @staticmethod
    def remove_edge(kb_content: str, edge_name: str) -> str:  # [KAIRO] fixed unreachable code
        lines = kb_content.split("\n")
        result = []
        skip = False

        for line in lines:
            stripped = line.strip()
            if stripped == f"### Edge: {edge_name}":
                skip = True
                continue
            if skip:
                if stripped.startswith("### ") or stripped.startswith("## "):
                    skip = False
                    result.append(line)
                continue
            result.append(line)

        return "\n".join(result)

    @staticmethod
    def format_edges_for_display(edges: list[dict]) -> list[str]:
        formatted = []
        for edge in edges:
            name = edge.get("name", "Unknown")
            source = edge.get("source", "?")
            target = edge.get("target", "?")
            edge_type = edge.get("type", "?")
            discovered = edge.get("discovered", "?")
            formatted.append(f"**{name}**: `{source}` → `{target}` ({edge_type}) _{discovered}_")
        return formatted

    @staticmethod
    def to_dot(edges: list[dict]) -> str:
        if not edges:
            return ""

        edge_colors = {
            "related_to": "#6366f1",
            "depends_on": "#f59e0b",
            "part_of": "#10b981",
            "leads_to": "#ef4444",
        }

        import re as _re
        _node_id_map = {}
        _counter = 0
        def _safe_id(name: str) -> str:
            nonlocal _counter
            if name not in _node_id_map:
                _counter += 1
                _node_id_map[name] = f"n{_counter}"
            return _node_id_map[name]

        lines = ["digraph KnowledgeGraph {"]
        lines.append("    rankdir=LR;")
        lines.append('    node [shape=box, style="rounded,filled", fillcolor="#f0f0f0", fontname="sans-serif"];')
        lines.append('    edge [fontname="sans-serif", fontsize=10];')

        nodes = set()
        for edge in edges:
            nodes.add(edge.get("source", "?"))
            nodes.add(edge.get("target", "?"))

        for node in sorted(nodes):
            lines.append(f'    {_safe_id(node)} [label="{node}"];')

        for edge in edges:
            source = _safe_id(edge.get("source", "?"))
            target = _safe_id(edge.get("target", "?"))
            edge_type = edge.get("type", "related_to")
            color = edge_colors.get(edge_type, "#6366f1")
            lines.append(f'    {source} -> {target} [label="{edge_type}", color="{color}", fontcolor="{color}"];')

        lines.append("}")
        return "\n".join(lines)

    @staticmethod
    def discover_edges_from_kb(kb_content: str) -> list[dict]:
        section_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
        sections = []
        for match in section_pattern.finditer(kb_content):
            sections.append({
                "name": match.group(1).strip(),
                "start": match.end(),
            })

        if len(sections) < 1:
            return []

        for i, sec in enumerate(sections):
            end = sections[i + 1]["start"] if i + 1 < len(sections) else len(kb_content)
            sec["content"] = kb_content[sec["start"]:end]

        skip_prefixes = ("🧩 Knowledge Graph", "📊 Growth Log", "⏰ Cron History")
        relevant = [s for s in sections if not any(s["name"].startswith(p) for p in skip_prefixes)]

        existing_edges = KnowledgeGraph.parse_edges(kb_content)
        existing_pairs = {
            (e.get("source", ""), e.get("target", ""), e.get("type", ""))
            for e in existing_edges
        }

        new_edges = []

        for i in range(len(relevant)):
            for j in range(i + 1, len(relevant)):
                s1, s2 = relevant[i], relevant[j]
                pair = (s1["name"], s2["name"], "related_to")
                if pair not in existing_pairs:
                    new_edges.append({
                        "source": s1["name"],
                        "target": s2["name"],
                        "type": "related_to",
                    })
                    existing_pairs.add(pair)

        for sec in relevant:
            keywords = set()
            for m in re.finditer(r"`([^`]+)`", sec["content"]):
                keywords.add(m.group(1).strip())
            for m in re.finditer(r"\*\*([^*]+)\*\*", sec["content"]):
                kw = m.group(1).strip()
                if len(kw) < 30:
                    keywords.add(kw)

            for kw in sorted(keywords):
                pair = (kw, sec["name"], "part_of")
                if pair not in existing_pairs:
                    new_edges.append({
                        "source": kw,
                        "target": sec["name"],
                        "type": "part_of",
                    })
                    existing_pairs.add(pair)

        return new_edges
