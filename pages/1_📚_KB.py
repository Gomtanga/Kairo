# [KAIRO]
import re
import streamlit as st
import os

from core import KBManager, KnowledgeGraph, LevelSystem


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text).strip()

st.set_page_config(page_title="KB.md - Kairo", page_icon="📚", layout="wide")
st.title("📚 Knowledge Base")

kb = KBManager()

with st.sidebar:
    LevelSystem.render_sidebar()
    with st.expander("📊 KB 통계", expanded=True):
        kb_content = kb.read()
        file_size = os.path.getsize(kb.kb_path)
        st.write(f"**파일 크기:** {file_size / 1024:.1f} KB")
        st.write(f"**예상 토큰:** {kb.estimate_tokens()} tokens")
        section_count = kb_content.count("\n## ")
        st.write(f"**섹션 수:** {section_count}개")
        if kb.needs_compression():
            st.warning("⚠️ 압축 권장: KB가 너무 커짐")

viewer_tab, editor_tab = st.tabs(["뷰어", "편집기"])

with viewer_tab:
    kb_content = kb.read()
    with st.container():
        st.markdown(strip_html_comments(kb_content))

    with st.expander("🧩 Knowledge Graph"):
        edges = KnowledgeGraph.parse_edges(kb_content)
        if edges:
            formatted = KnowledgeGraph.format_edges_for_display(edges)
            for edge in formatted:
                st.markdown(f"- {edge}")
        else:
            st.info("Knowledge Graph에 edge가 없습니다.")

with editor_tab:
    current_content = kb.read()
    edited_content = st.text_area("KB.md 내용", value=current_content, height=600)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 저장", use_container_width=True):
            kb.write(edited_content)
            st.toast("KB.md가 저장되었습니다!", icon="✅")
            st.rerun()

    with col2:
        if st.button("↩️ 백업 복원", use_container_width=True):
            success = kb.restore_backup()
            if success:
                st.toast("백업이 복원되었습니다!", icon="✅")
                st.rerun()
            else:
                st.warning("백업 파일을 찾을 수 없습니다.")

    with col3:
        if st.button("🔄 초기화", use_container_width=True):
            st.session_state.show_init_confirm = True

        if st.session_state.get("show_init_confirm", False):
            st.warning("정말로 초기화하시겠습니까? 모든 데이터가 삭제됩니다.")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("예, 초기화합니다", key="confirm_init_yes"):
                    kb._create_template()
                    st.session_state.show_init_confirm = False
                    st.toast("KB.md가 초기 템플릿으로 재설정되었습니다!", icon="✅")
                    st.rerun()
            with col_b:
                if st.button("취소", key="cancel_init"):
                    st.session_state.show_init_confirm = False
                    st.rerun()
