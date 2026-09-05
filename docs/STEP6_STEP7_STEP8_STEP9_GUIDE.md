# STEP 6〜9 学習ガイド

この4 STEP は、これまで作った部品を「Incident Response Agent」として接続する区間です。

---

# 全体像

```text
STEP 6                    STEP 7              STEP 8             STEP 9

Gemini                    Risk Policy         Approved action     Verify
  │                          │                    │                 │
  │ chooses read tool        │ interrupt()        │ Python maps     │ read MCP
  v                          v                    v                 v
Read MCP Tool loop  ->   Human approval  ->  Write MCP Tool  -> Recovered?
                                                                   │
                                                          No ------+
                                                                   v
                                                             investigate again
```

最重要なのは「LLM に任せる範囲が段階ごとに狭く定義されている」ことです。

---

# STEP 6 — Agentic Investigation

## Graph

`src/jboss_agent/graph/agentic_investigation_graph.py`

```text
START
  ↓
prepare_investigation
  ↓
investigate
  │
  ├─ AIMessage.tool_calls あり
  │       ↓
  │   ToolNode(read_tools)
  │       ↓
  │   ToolMessage
  │       ↓
  │   record_tool_evidence
  │       ↓
  │   investigate
  │
  └─ tool_calls なし / 上限到達
          ↓
       diagnose
          ↓
         END
```

## MessagesState

STEP 6 の `IncidentState` は `MessagesState` を継承しています。

```python
class IncidentState(MessagesState, total=False):
    ...
```

`messages` には例えば次の順で積まれます。

```text
SystemMessage
HumanMessage
AIMessage(tool_calls=[get_thread_pool_status])
ToolMessage(...)
AIMessage(tool_calls=[get_recent_config_changes])
ToolMessage(...)
AIMessage("enough evidence")
```

`ToolNode` が返した `ToolMessage` を次の Gemini 呼び出しが読むため、Agent が「調査結果を見て次の調査を決める」ループになります。

## LLM に任せること

```text
「次にどの read Tool を使うべきか」
```

例えば thread pool が怪しいなら Gemini が:

```text
get_thread_pool_status
get_recent_config_changes
get_server_health
```

などから必要なものを選びます。

## LLM に任せないこと

- 最大調査回数
- write Tool の利用可否
- Risk Policy
- 設定値の上限/下限

`MAX_INVESTIGATION_ROUNDS` に達したら LangGraph/Python が強制的に `diagnose` へ進めます。

## STEP 5 との違い

STEP 5:

```text
Python が get_server_health を選ぶ
```

STEP 6:

```text
Gemini が read-only Tool の中から選ぶ
```

これが deterministic tool execution と agentic tool selection の違いです。

---

# STEP 7 — Human-in-the-loop

## Graph

`src/jboss_agent/graph/approval_graph.py`

```text
START
  ↓
validate_proposed_action
  │
  ├─ BLOCKED → END
  │
  └─ approval
        ↓
     interrupt(payload)
        │
        │ graph stops
        │ checkpoint saved
        │
        └── Command(resume=...) + same thread_id
                 ↓
          approval Node starts again
                 ↓
          interrupt() returns resume value
                 ↓
         APPROVED / REJECTED / BLOCKED
```

## interrupt は「関数の途中から再開」ではない

ここはかなり重要です。

```python
response = interrupt(payload)
```

初回はここで Graph が止まります。

resume 時には approval Node が **先頭から再実行**され、同じ `interrupt()` が今度は `Command(resume=...)` の値を返します。

そのため、これは危険です。

```python
send_email()      # resume 時にも再実行され得る
response = interrupt(...)
```

今回の実装は interrupt より前で payload を作るだけです。

```python
payload = {...}   # pure / idempotent
response = interrupt(payload)
```

## thread_id

Incident ごとに:

```text
incident:<uuid>
```

を使います。

```python
config = {
    "configurable": {
        "thread_id": "incident:inc-123"
    }
}
```

resume も同じ値です。

```python
graph.invoke(
    Command(resume={"decision": "approve"}),
    config=config,
)
```

別の `thread_id` を使うと、別 Incident の State なので再開できません。

## Checkpointer

`CHECKPOINT_BACKEND=memory`

```text
InMemorySaver
```

学習・テスト向けです。Python プロセス終了で消えます。

`CHECKPOINT_BACKEND=sqlite`

```text
AsyncSqliteSaver
```

`.data/checkpoints.sqlite` に保存します。

確認:

```bash
make step7-pause
# Python process exits while pending

make step7-resume
# same thread_id is restored from SQLite
```

## Edit and approve

resume payload:

```json
{
  "decision": "edit_and_approve",
  "proposed_value": 100
}
```

人間が値を編集しても、その値を無条件には信用しません。

```text
Human edit
   ↓
Risk Policy validation again
   ↓
valid   -> APPROVED
invalid -> BLOCKED
```

---

# STEP 8 — MCP Write Tools

## MCP Server capability

Fake JBoss MCP Server に4つ追加しています。

```text
set_thread_pool_max_threads
set_datasource_max_pool_size
restart_deployment
reload_server
```

ただし read Agent には渡しません。

```text
MCP Server
 ├─ read tools  ─── load_fake_jboss_read_tools()  ──> Investigation LLM
 └─ write tools ─── load_fake_jboss_write_tools() ──> approved execution Graph
```

MCP Server に write capability が存在することと、LLM に write capability を与えることは別問題です。

## write Tool を誰が選ぶ？

Geminiではありません。

```python
proposed_action["type"]
```

を Python が変換します。

```text
SET_THREAD_POOL_MAX_THREADS
       ↓ Python
set_thread_pool_max_threads
```

そして `AIMessage.tool_calls` をプログラムで構築し、`ToolNode(write_tools)` に渡しています。

```text
Human Approved
     ↓
Python mapping
     ↓
AIMessage(tool_calls=[...])
     ↓
ToolNode
     ↓
MCP write
```

ここで AIMessage を使うのは **LLM が決めたからではなく、ToolNode の標準入力形式を使うため**です。

## Validation

`src/jboss_agent/domain/risk_policy.py`

例:

```text
thread pool: 1 - 200
```

さらに Fake JBoss 側でも同じ範囲を検証します。

```text
LLM proposal
  ↓
Domain policy validation
  ↓
Human approval
  ↓
Domain policy validation
  ↓
MCP boundary validation
  ↓
Fake JBoss write
```

多層にしています。

---

# STEP 9 — Recovery Loop

`src/jboss_agent/graph/incident_graph.py`

STEP 6〜8 を接続した Graph です。

```text
START
  ↓
prepare_investigation
  ↓
investigate ←──────────────────────────────┐
  ↓                                         │
read MCP Tool loop                          │
  ↓                                         │
diagnose                                    │
  ↓                                         │
Risk Policy                                 │
  ↓                                         │
interrupt approval                          │
  ↓                                         │
write MCP                                   │
  ↓                                         │
verify_recovery                             │
  │                                         │
  ├─ recovered ────────────────→ END        │
  │                                         │
  └─ not recovered                          │
          ↓                                 │
     recovery_attempts                      │
          │                                 │
          ├─ max reached → fail_safe → END  │
          │                                 │
          └─ prepare_retry ─────────────────┘
```

## Verify はなぜ LLM ではない？

例えば thread pool の復旧条件は明確です。

```text
server status == UP
request_error_rate < 5%
active_threads <= max_threads
queue_size == 0
rejected_tasks == 0
```

このような機械的条件を毎回 Gemini に判断させる必要はありません。

```text
曖昧な原因調査      -> LLM
明確な復旧条件      -> Python
状態取得             -> MCP
ループ制御           -> LangGraph
```

## 無限ループ防止

```env
MAX_RECOVERY_ATTEMPTS=2
```

例えば2回失敗したら:

```text
fail_safe
  ↓
END
```

として人間へのエスカレーション対象にします。

Agent が「まだ調べたい」と言っても、この上限は LLM ではなく Graph が保証します。

---

# State がどう変わるか

代表例です。

```text
開始
investigation_count = 0
recovery_attempts    = 0
approval_status      = None

STEP 6 tool loop
investigation_count = 1, 2, ...
evidence            = MCP Tool results

診断後
diagnosis       = {...}
proposed_action = {...}

Risk Policy 後
risk_level      = MEDIUM
approval_status = PENDING

interrupt
checkpoint に State 保存

resume
approval_status = APPROVED

write 後
execution_result  = {...}
recovery_attempts = 1

verify 後
recovered = True / False
```

---

# Local Tool と MCP の現在地

STEP 9 時点:

```text
LOCAL TOOL
send_teams_alert
  └─ Teams HTTP POST

MCP READ TOOL
read_server_log
get_server_health
get_thread_pool_status
get_datasource_status
get_deployment_status
get_recent_config_changes

MCP WRITE TOOL
set_thread_pool_max_threads
set_datasource_max_pool_size
restart_deployment
reload_server
```

禁止:

```text
execute_jboss_cli(command)
execute_shell(command)
```

Agent に任意コマンド実行権限は与えません。

---

# 実行順

```bash
make test
make step6
make step7
make step8
make step9
```

SQLite persistence:

```bash
make step7-pause
make step7-resume
```

次の STEP 10 では、この Graph の中に `sleep(180)` を入れるのではなく、Graph の外に Scheduler を置きます。
