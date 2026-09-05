# Architecture / Responsibility Design

## 1. 最重要方針

このプロジェクトでは、すべてを Agent に寄せない。

責務を以下に分離する。

```text
Scheduler
  定期起動だけ

LangGraph
  状態遷移・分岐・ループ・HITL

Gemini
  曖昧なログ解釈・仮説生成・追加調査判断

Local Tool
  Teams 通知

MCP
  JBoss という外部システムの能力公開

Domain Logic
  Risk policy / validation / business rules

Simulator
  学習用 Fault injection / Ground truth

Streamlit
  Visualization / approval UI
```

---

## 2. ディレクトリ構成

```text
src/jboss_agent/
├── graph/
│   ├── monitoring_graph.py
│   ├── incident_graph.py
│   ├── state.py
│   ├── nodes/
│   │   ├── collect_logs.py
│   │   ├── analyze_logs.py
│   │   ├── notify_teams.py
│   │   ├── investigate.py
│   │   ├── propose_action.py
│   │   ├── approval.py
│   │   ├── execute.py
│   │   └── verify.py
│   └── routes/
│       ├── monitoring_routes.py
│       └── incident_routes.py
│
├── domain/
│   ├── models.py
│   ├── risk_policy.py
│   └── validation.py
│
├── local_tools/
│   └── teams.py
│
├── mcp_client/
│   ├── client.py
│   └── tool_registry.py
│
├── jboss/
│   ├── ports.py
│   ├── fake_operations.py
│   └── real_operations.py
│
├── simulator/
│   ├── fault_injector.py
│   ├── ground_truth.py
│   └── scenarios.py
│
├── runtime/
│   ├── service.py
│   └── store.py
│
├── scheduler/
│   └── monitor_scheduler.py
│
├── evaluation/
│   ├── metrics.py
│   └── runner.py
│
└── ui/
    └── streamlit_app.py
```

---

## 3. LangGraph と Tool の境界

### Local Tool

Teams は `@tool` で実装する。

目的は LangChain/LangGraph の Tool Calling を直接学ぶこと。

```text
Gemini
  -> tool_calls: send_teams_alert
  -> tools_condition
  -> ToolNode
  -> local Python function
```

### MCP Tool

JBoss 操作は外部 capability として扱う。

```text
Gemini / Graph
  -> MCP adapter
  -> JBoss MCP Server
  -> Fake or Real JBoss adapter
```

この差を意識する。

---

## 4. なぜログ取得は LLM に任せないか

3分に1回必ずログ増分を取るという要件は決定論的である。

そのため Monitoring Graph の `collect_logs` は通常 Node とし、毎回 LLM に「ログを取るべきですか？」とは聞かない。

一方 Incident Response では、次に何を調べるべきかは状況依存なので LLM に read-only MCP Tool を選ばせる。

この2つを同じプロジェクトで比較することで、

- deterministic orchestration
- agentic tool selection

の違いを学ぶ。

---

## 5. Human-in-the-loop の境界

承認前:

```text
Agent has read-only tools only.
```

承認後:

```text
Graph chooses validated write action.
```

write Tool は最初から Investigation Agent に渡さない。

---

## 6. Persistence

開発初期:

```text
InMemorySaver
```

HITL 学習段階:

```text
SQLite-backed checkpointer or equivalent durable local store
```

最終デモでは Dev Container 再起動後も pending approval を復元できる構成を目標にする。

---

## 7. Scheduler

APScheduler 等の軽量 Scheduler を使用する。

責務:

```python
monitor_graph.invoke(...)
```

のみ。

Scheduler 内に Incident 判定や業務ロジックを書かない。

---

## 8. Teams Tool

`send_teams_alert` は以下を隠蔽する。

- Webhook URL
- HTTP POST
- timeout
- retry
- JSON payload
- duplicate prevention

LLM からは:

```text
send_teams_alert(server_id, incident_id, severity, category, summary)
```

という意味のある Tool に見せる。

---

## 9. Fake JBoss

Fake JBoss は「テストデータ」ではなく、状態を持つ小さなシミュレータにする。

例:

```json
{
  "thread_pool": {
    "max_threads": 80,
    "active_threads": 12,
    "queue_size": 0
  },
  "datasource": {
    "max_pool_size": 30,
    "active_count": 8
  },
  "deployment": {
    "status": "OK"
  }
}
```

Fault Injector がこの状態とログを変更する。

Agent は Ground Truth を参照できない。


## 10. STEP 10〜12 operational boundary

最終デモでは保存先を3つに分離する。

```text
LangGraph Checkpointer
  Graph State / cursor / pending interrupt

Runtime SQLite
  Dashboard用のscan/incident/activity metadata

Simulator Ground Truth SQLite
  Agentから隔離した正解ラベル
```

Scheduler と Streamlit は同じ `OperationalAgentService` を呼ぶ。
Scheduler/UI内に診断・Risk Policy・write Tool選択ロジックを重複実装しない。

Evaluation は実Graphを10〜30回実行するが、評価中のTeams実送信だけは dependency injection したdry-run notifierで無効化する。
