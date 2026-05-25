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
    def remove_edge(kb_content: str, edge_name: str) -> str:
        lines = kb_content.split("\n")
        result = []
        skip = False
        i = 0

        while i < len(lines):
            stripped = lines[i].strip()
            if stripped == f"### Edge: {edge_name}":
                skip = True
                i += 1
                continue
                if skip:
                    if stripped.startswith("### ") or stripped.startswith("## "):
                        skip = False
                        result.append(lines[i])
                    i += 1
                continue
            result.append(lines[i])
            i += 1

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
