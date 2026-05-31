# [KAIRO]
import streamlit as st
import pandas as pd
from core import KBManager, KnowledgeGraph, LevelSystem


@st.cache_resource
def get_kb_manager():
    return KBManager()


st.set_page_config(page_title="지식 그래프 - Kairo", page_icon="🧩", layout="wide")
st.title("🧩 Knowledge Graph")

# Read KB content
kb = get_kb_manager()
kb_content = kb.read()

# Parse edges
edges = KnowledgeGraph.parse_edges(kb_content)

with st.sidebar:
    LevelSystem.render_sidebar("지식 그래프")
    st.divider()
    st.metric("📊 Edge 수", len(edges))

# Main layout: graph + details
if edges:
    # --- Graphviz visualization ---
    st.subheader("📈 그래프 시각화")
    dot_string = KnowledgeGraph.to_dot(edges)
    if dot_string:
        st.graphviz_chart(dot_string, use_container_width=True)

    # --- Edge list as dataframe ---
    st.subheader("📋 Edge 목록")

    # Build dataframe from edges
    df_data = []
    for edge in edges:
        df_data.append({
            "Edge": edge.get("name", "Unknown"),
            "Source": edge.get("source", "?"),
            "Target": edge.get("target", "?"),
            "Type": edge.get("type", "?"),
            "Discovered": edge.get("discovered", "?"),
        })

    df = pd.DataFrame(df_data)

    # Display edge count and dataframe
    st.caption(f"총 **{len(edges)}개** edge")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # --- Raw DOT output (collapsible) ---
    with st.expander("🔧 DOT 소스 보기"):
        st.code(dot_string, language="dot")
else:
    st.info(
        "📭 Knowledge Graph에 등록된 edge가 없습니다.\n\n"
        "KB.md의 `## 🧩 Knowledge Graph (자동 발견)` 섹션에 "
        "edge가 추가되면 여기에 시각화가 표시됩니다."
    )
