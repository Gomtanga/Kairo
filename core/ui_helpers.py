# [KAIRO] Streamlit UI rendering helpers
import json
import os
import re
from datetime import datetime

import streamlit as st


def render_markdown_tables(text: str):
    import pandas as pd

    table_pattern = re.compile(r'^\|.+\|$\n^\|[-:\s|]+\|$\n((?:^\|.+\|$\n?)+)', re.MULTILINE)
    for match in table_pattern.finditer(text):
        rows = [line.strip() for line in match.group(0).strip().split('\n') if line.strip()]
        if len(rows) < 3:
            continue
        headers = [c.strip() for c in rows[0].split('|') if c.strip()]
        data_rows = []
        for row in rows[2:]:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            data_rows.append(cells)
        if headers and data_rows:
            df = pd.DataFrame(data_rows, columns=headers)
            row_height = 35
            height = min(35 + row_height * (len(data_rows) + 1), 400)
            st.dataframe(df, width="stretch", hide_index=True, height=height)


def render_tool_call_widgets(tool_calls: list[dict]) -> bool:
    has_any = False
    for tc in tool_calls:
        name = tc.get("name", "")
        args = tc.get("arguments", {})

        if name == "create_form":
            has_any = True
            with st.expander(f"📝 {args.get('title', 'Form')}", expanded=True):
                field_data = {}
                for field in args.get("fields", []):
                    fname = field.get("name", "")
                    ftype = field.get("field_type", "text")
                    fhint = field.get("hint", "")
                    if ftype == "number":
                        field_data[fname] = st.number_input(fname, help=fhint)
                    elif ftype == "textarea":
                        field_data[fname] = st.text_area(fname, help=fhint)
                    elif ftype == "select":
                        options = [o.strip() for o in fhint.split(",")] if fhint else []
                        field_data[fname] = st.selectbox(fname, options) if options else st.text_input(fname, help=fhint)
                    else:
                        field_data[fname] = st.text_input(fname, help=fhint)
                if st.button(f"제출: {args.get('title', 'Form')}", key=f"form_{args.get('title', 'form')}"):
                    st.toast(f"✅ {args.get('title', 'Form')} 제출됨!")

        elif name == "create_table":
            has_any = True
            headers = args.get("headers", [])
            rows = args.get("rows", [])
            if headers and rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=headers)
                row_height = 35
                height = min(35 + row_height * (len(rows) + 1), 400)
                st.dataframe(df, width="stretch", hide_index=True, height=height)

        elif name == "create_chart":
            has_any = True
            labels = args.get("labels", [])
            values = args.get("values", [])
            chart_type = args.get("chart_type", "bar")
            chart_data = {"항목": labels, "값": values}
            if chart_type == "line":
                st.line_chart(chart_data, x="항목", y="값", width="stretch")
            elif chart_type == "pie":
                import pandas as pd
                st.pyplot(
                    pd.DataFrame(chart_data).plot(
                        kind="pie", y="값", labels=labels, autopct="%1.1f%%", figsize=(6, 4)
                    ).figure
                )
            else:
                st.bar_chart(chart_data, x="항목", y="값", width="stretch")

        elif name == "create_button":
            has_any = True
            label = args.get("label", "버튼")
            action = args.get("action", "")
            if st.button(f"🔘 {label}", key=f"btn_{label}"):
                st.info(f"실행: {action}")

    return has_any


SAVED_MESSAGES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_messages.json")


def load_saved_messages() -> list[dict]:
    if os.path.exists(SAVED_MESSAGES_PATH):
        with open(SAVED_MESSAGES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_saved_messages(messages: list[dict]):
    with open(SAVED_MESSAGES_PATH, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)
