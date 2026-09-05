# Learning Roadmap

この順番で実装する。

各 STEP は必ず単独で動作確認してから次へ進む。

---

## STEP 0 — Environment

### 作るもの

- Dev Container
- Dockerfile
- `.env`
- Gemini 接続確認
- Streamlit Hello World

### 学ぶこと

- Python 実行環境をコンテナに閉じる
- Secret をコードから分離する

### 完了条件

- Dev Container が起動する
- Gemini に1回問い合わせできる
- Streamlit がブラウザ表示できる

---

## STEP 1 — LangGraph Core

### 作るもの

Fake なログ文字列を State に入れ、Node を順番に通す最小 Graph。

```text
START -> collect_fake_log -> simple_check -> END
```

### 学ぶこと

- State
- Node
- Edge
- `compile()`
- `invoke()`

### この STEP ではやらない

- LLM
- MCP
- Tool
- HITL
- Scheduler

---

## STEP 2 — LLM Routing

### 作るもの

Gemini にログを Structured Output で分類させる。

```text
NORMAL
THREAD_POOL
DATASOURCE_POOL
DEPLOYMENT
UNKNOWN
```

Conditional Edge で分岐。

### 学ぶこと

- LLM と Graph の責務差
- Structured Output
- Conditional Edge

---

## STEP 3 — Monitoring / Cursor

### 作るもの

Fake server.log を用意し、前回 cursor 以降だけ読む。

### 学ぶこと

- State persistence の前段
- 差分監視
- LLM コストを抑える設計

---

## STEP 4 — Local Tool: Teams

### 作るもの

`send_teams_alert` を `@tool` で実装。

`ToolNode` と `tools_condition` を使う。

### 学ぶこと

- Tool schema
- Tool description
- LLM tool call
- ToolNode
- Tool result
- Local Tool と MCP の違い

### テスト

`TEAMS_DRY_RUN=true` なら実際に Teams へ送らず console に payload を出す。

---

## STEP 5 — MCP Read Tools

### 作るもの

Fake JBoss MCP Server。

read-only Tool を提供する。

### 学ぶこと

- MCP Server
- MCP Client
- `langchain-mcp-adapters`
- MCP Tool を Agent に渡す方法

---

## STEP 6 — Agentic Investigation

### 作るもの

Incident Agent が自分で必要な read Tool を選ぶ。

例:

```text
get_thread_pool_status
get_server_health
get_recent_config_changes
```

### 学ぶこと

- LLM-driven tool selection
- Tool loop
- MessagesState
- investigation limit

---

## STEP 7 — Human-in-the-loop

### 作るもの

対処案を生成し、write 操作前に `interrupt()`。

### 学ぶこと

- Checkpointer
- thread_id
- interrupt
- `Command(resume=...)`
- resume 時の Node 再実行
- idempotency

---

## STEP 8 — MCP Write Tools

### 作るもの

承認後のみ Fake JBoss を変更する。

### 学ぶこと

- read/write capability 分離
- validation
- Tool side effect

---

## STEP 9 — Recovery Loop

### 作るもの

変更後に状態を再確認。

```text
Recovered -> END
Not recovered -> investigation
```

### 学ぶこと

- Loop
- 最大試行回数
- fail-safe

---

## STEP 10 — Scheduler

### 作るもの

APScheduler から 180 秒ごとに Monitoring Graph を起動。

### 学ぶこと

- Scheduler と workflow の責務分離
- fixed monitoring thread_id

---

## STEP 11 — Streamlit UI

### 作るもの

- Server status
- Polling status
- Agent activity
- Inject Random Event
- Approval UI
- Ground Truth comparison

### 学ぶこと

- Graph と UI の接続
- pending interrupt の表示・resume

---

## STEP 12 — Evaluation

### 作るもの

10〜30回ランダムイベントを流し、診断精度を表示。

### 学ぶこと

- Agent 評価
- False Positive
- Tool call count
- recovery success

---

## STEP 13 — Real JBoss Adapter (Optional)

### 作るもの

Fake MCP Server の内部実装を JBoss CLI / Management API に差し替える。

### 学ぶこと

- Interface boundary
- MCP の価値
- Agent/Graph を変更せず外部実装を交換する設計
