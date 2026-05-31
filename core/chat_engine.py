# [KAIRO] Chat engine — pure response parsing and tool execution logic
import re

from core.tool_system import ToolSystem


def extract_kb_updates(response: str) -> tuple[str, list[str]]:
    display = response
    updates = re.findall(r"```kb-update\n(.*?)```", response, re.DOTALL)
    if updates:
        display = re.sub(r"```kb-update\n.*?```\n?", "", response, flags=re.DOTALL).strip()
    return display, updates


def extract_graph_edges(response: str) -> list[dict]:
    blocks = re.findall(r"```kb-graph\n(.*?)```", response, re.DOTALL)
    edges = []
    for block in blocks:
        edge = {}
        for line in block.strip().split("\n"):
            match = re.match(r"(\w+):\s*(.+)", line.strip())
            if match:
                edge[match.group(1)] = match.group(2).strip()
        if "source" in edge and "target" in edge:
            edges.append(edge)
    return edges


def extract_cron_suggestions(response: str) -> list[dict]:
    blocks = re.findall(r"```kb-cron\n(.*?)```", response, re.DOTALL)
    suggestions = []
    for block in blocks:
        cron = {}
        for line in block.strip().split("\n"):
            match = re.match(r"(\w+):\s*(.+)", line.strip())
            if match:
                cron[match.group(1)] = match.group(2).strip()
        if "name" in cron and "cron" in cron:
            suggestions.append(cron)
    return suggestions


def extract_tool_commands(response: str) -> list[str]:
    commands = re.findall(r"---TOOL---\s*\ncommand:\s*(.+?)\s*\n(?:---TOOL---)?", response)
    seen = []
    for cmd in commands:
        cmd = cmd.strip()
        if cmd and cmd not in seen:
            seen.append(cmd)
    return seen


def execute_tool_loop(llm_client, chat_messages, kb_content, raw_response, max_rounds=3):
    all_tool_results = []
    current_response = raw_response
    executed_commands = set()

    for round_num in range(max_rounds):
        commands = extract_tool_commands(current_response)
        new_commands = [c for c in commands if c not in executed_commands]
        if not new_commands:
            break

        tool_outputs = []
        for cmd in new_commands:
            executed_commands.add(cmd)
            result = ToolSystem.run_safe_command(cmd)
            all_tool_results.append({"command": cmd, **result})
            if result["success"]:
                tool_outputs.append(f"$ {cmd}\n{result['output']}")
            else:
                tool_outputs.append(f"$ {cmd}\nERROR: {result['error']}")

        if not tool_outputs:
            break

        tool_context = "\n".join(tool_outputs)
        followup_messages = chat_messages + [
            {"role": "assistant", "content": current_response},
            {"role": "user", "content": f"[TOOL RESULTS]\n{tool_context}\n\n위 도구 실행 결과를 반영하여 답변을 완성해주세요. 더 이상 ---TOOL--- 마커를 사용하지 마세요."},
        ]
        followup_result = llm_client.chat(followup_messages, kb_content=kb_content)
        current_response = followup_result.get("content", "") if isinstance(followup_result, dict) else followup_result

    return current_response, all_tool_results
