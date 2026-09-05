# STEP 3 / 4 / 5 Learning Guide

この3 STEP は、LangGraph 学習で混ざりやすい責務を順番に分離するためのまとまりです。

```text
STEP 3: 決定論的な監視
  Fake server.log -> cursor差分 -> 必要なときだけGemini

STEP 4: アプリ内のローカルTool
  Gemini -> tool call -> ToolNode -> send_teams_alert -> Gemini

STEP 5: 外部システム能力としてのMCP
  LangGraph -> MCP Tool -> stdio -> Fake JBoss MCP Server
```

---

## STEP 3 — Monitoring / Cursor

### 目的

毎回 `server.log` 全体を Gemini に送るのではなく、前回読了位置以降だけを読む。

Fake JBoss の cursor は **UTF-8 byte offset** として実装している。

```text
server.log
0 ---------------------------------------------------- 184
                                                       ^
                                                previous cursor

新規ログ追記

0 ---------------------------------------------------- 184 -------- 261
                                                       ^            ^
                                                      from          to
```

### Graph

```text
START
  |
  v
collect_logs
  |
  +-- has_new_logs=false --> no_new_logs --> END
  |
  +-- has_new_logs=true
          |
          v
      analyze_logs (Gemini)
          |
          v
    Conditional Edge
       NORMAL / THREAD_POOL / ...
          |
          v
         END
```

### State の変化

入力:

```python
{
    "server_id": "jboss-01",
    "previous_log_cursor": 184,
}
```

`collect_logs` 後:

```python
{
    "previous_log_cursor": 184,
    "current_log_cursor": 261,
    "new_log_lines": ["...new line..."],
    "has_new_logs": True,
    "log_text": "...new line...",
}
```

次回呼び出しでは `current_log_cursor` を `previous_log_cursor` として渡す。

STEP 3 ではまだ Checkpointer を使わない。cursor を明示的に受け渡すことで、State persistence の意味を先に理解する。Checkpointer / `thread_id` は STEP 7 で扱う。

### LLM に任せること

新規ログの意味解釈だけ。

### Python に任せること

- ファイルを読む
- cursor を計算する
- 新規ログの有無を判定する
- 新規ログがなければ Gemini を呼ばない

これは曖昧な判断ではないため LLM に聞く必要がない。

### 実行

```bash
make step3
```

CLI は次を連続実行する。

1. 正常ログを追記 → 差分を Gemini が解析
2. 何も追記しない → Gemini をスキップ
3. Thread Pool 系ログを追記 → 追加分だけ Gemini が解析

---

## STEP 4 — Local Tool: Teams

### 目的

LangChain Tool Calling と LangGraph `ToolNode` を体験する。

Teams は JBoss の capability ではないため MCP にしない。

```text
src/jboss_agent/local_tools/teams.py

@tool
def send_teams_alert(...):
    ...
```

### Graph

```text
START
  |
  v
notification_guard   <- Python
  |
  +-- incidentなし / 通知済み --> skip_notification --> END
  |
  v
prepare_teams_request
  |
  v
call_teams_tool       <- Gemini + bind_tools
  |
  v
tools_condition
  |
  +-- tool_callsなし --> END
  |
  +-- tool_callsあり
          |
          v
        tools         <- ToolNode([send_teams_alert])
          |
          v
     finalize_teams   <- ToolMessageをStateへ反映 + Geminiで結果要約
          |
          v
         END
```

### なぜ `tools_condition` を使うのか

Gemini の `AIMessage` に `tool_calls` があるかを LangGraph が見て、

- Tool 実行へ進む
- Tool がなければ終了する

を分岐するため。

```text
AIMessage
  tool_calls=[...]
        |
        v
tools_condition
        |
        v
ToolNode
```

### Tool schema

`TeamsAlertInput` を Pydantic で定義している。

```text
server_id
incident_id
severity
category
confidence
summary
```

LLM から見える Tool は、単なる Python 関数名ではなく、**名前・description・引数schemaを持つ capability** になる。

### Dry run

`.env`:

```env
TEAMS_DRY_RUN=true
```

この場合、HTTP POST は行わず payload をログ出力する。

実行:

```bash
make step4
```

### 二重送信防止

二段構えにしている。

1. Graph State の `teams_notified=true` なら Tool flow 自体へ進まない
2. Tool 内でも同一 `incident_id` は `duplicate_skipped`

後者は side effect を idempotent にするための保険。

### Local Tool と MCP の違い

Teams Tool:

```text
LangGraph process
    |
    +-- send_teams_alert()  <-- 同じPythonアプリの中
```

MCP Tool:

```text
LangGraph process
    |
    +-- MCP Client
            |
          protocol
            |
      MCP Server process
            |
        Fake JBoss
```

---

## STEP 5 — MCP Read Tools

### 目的

JBoss 操作を Agent アプリ内部の関数として直接公開せず、MCP Server の capability として公開する。

### Fake JBoss MCP Server

```text
src/jboss_agent/mcp_server/fake_jboss_server.py
```

read-only Tool:

```text
read_server_log
get_server_health
get_thread_pool_status
get_datasource_status
get_deployment_status
get_recent_config_changes
```

STEP 5 では write Tool は存在しない。

以下も存在しない。

```text
execute_jboss_cli
execute_shell
```

### MCP Client

```text
MultiServerMCPClient
    |
    | stdio
    v
python -m jboss_agent.mcp_server.fake_jboss_server
```

`langchain-mcp-adapters` が MCP Tool を LangChain Tool に変換する。

そのため LangGraph 側から見ると、STEP 4 のローカル Tool と MCP Tool はどちらも `ToolNode` に渡せる。

```python
tools = await client.get_tools()
ToolNode(tools)
```

しかし **Tool がどこで実行されるか** が違う。

### STEP 5 Graph

STEP 6 との違いを明確にするため、STEP 5 では Gemini に Tool を選ばせない。

```text
START
  |
  v
request_mcp_tool      <- Python が get_server_health の tool_call を作る
  |
  v
ToolNode(MCP tools)
  |
  v
MCP stdio server
  |
  v
ToolMessage
  |
 END
```

ここでは「MCP 接続・Tool discovery・Tool execution」だけを確認する。

次の STEP 6 で初めて、Gemini に複数の read-only MCP Tool を渡し、状況に応じて自分で Tool を選ばせる。

### 実行

```bash
make step5
```

期待する表示イメージ:

```text
Discovered MCP read tools:
  - get_datasource_status
  - get_deployment_status
  - get_recent_config_changes
  - get_server_health
  - get_thread_pool_status
  - read_server_log

STEP 5 graph: Python emits tool_call -> ToolNode -> MCP stdio server -> ToolMessage
requested_tool=get_server_health
...
```

### MCP SDK バージョンについて

2026-09 時点で MCP Python SDK 2.x が stable だが、`langchain-mcp-adapters 0.3.2` は dependency として `mcp>=1.24,<2` を要求する。

この教材では **LangChain adapter を確実に動かすことを優先し MCP SDK 1.x を明示的に pin** している。

```toml
langchain-mcp-adapters==0.3.2
mcp[cli]>=1.24,<2
```

adapter が MCP SDK 2.x に対応した段階で、この pin を更新する。

---

# 3 STEP をまとめて見た責務分離

| 項目 | STEP 3 | STEP 4 | STEP 5 |
|---|---|---|---|
| 主題 | 差分監視 | Local Tool | MCP Tool |
| LLM | ログ意味解析 | Tool call生成・結果要約 | 使わない |
| Python | cursor/分岐 | 通知guard/idempotency | MCP接続設定/安全なTool registry |
| LangGraph | State/Conditional Edge | messages/ToolNode/tools_condition | ToolNode |
| 外部境界 | ファイル | Teams Webhook | MCP protocol |
| JBoss操作 | Fake reader直呼び | なし | MCP Server経由 |

一番重要なのは、すべてを Agent にしないこと。

```text
曖昧な意味判断              -> LLM
状態遷移                    -> LangGraph
決定論的ルール              -> Python
アプリ固有通知              -> Local Tool
外部システム capability     -> MCP
```
