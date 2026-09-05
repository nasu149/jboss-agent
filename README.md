# LangGraph JBoss Incident Response Agent — STEP 0〜9 実装版

このリポジトリは、LangGraph を「実際に動く題材」で学ぶためのスターターパックです。

**現在は `LEARNING_ROADMAP.md` の STEP 0〜9 まで実装済みです。** 各 STEP の学習用 Graph を残しているため、段階ごとの差分を比較できます。

目的は JBoss EAP の運用自動化製品を完成させることではなく、次の要素を一つの題材で体系的に学ぶことです。

- LangGraph の State / Node / Edge / Conditional Edge
- LLM による分類・分岐・追加調査
- LangChain/LangGraph のローカル Tool (`@tool`, `ToolNode`, `tools_condition`)
- MCP Tool とローカル Tool の使い分け
- Human-in-the-loop (`interrupt`, `Command(resume=...)`)
- Checkpoint / `thread_id`
- ループによる再診断・復旧確認
- 外部 Scheduler による定期監視
- Streamlit による学習用 UI

## 完成イメージ

3分ごとに Monitoring Graph を起動し、JBoss の `server.log` の増分を取得します。

1. 増分がなければ終了
2. 増分があれば Gemini が障害兆候を判定
3. 障害の疑いがあれば Teams に通知
4. Incident Response Graph を起動
5. LLM が read-only MCP Tool を選び、自律的に追加調査
6. 原因と対処案を生成
7. 変更操作なら Human-in-the-loop で承認待ち
8. 承認後に write MCP Tool で JBoss 設定変更
9. 復旧確認
10. 直らなければ再調査

障害注入は UI からできますが、Agent には注入した障害種別を知らせません。正常ログだけが増えるケースも混ぜ、False Positive も評価します。

## Tool の役割分担

### MCP Tool

JBoss への操作は MCP Server 側に置きます。

例:

- `read_server_log`
- `get_server_health`
- `get_thread_pool_status`
- `get_datasource_status`
- `get_deployment_status`
- `get_recent_config_changes`
- `set_thread_pool_max_threads`
- `set_datasource_max_pool_size`
- `restart_deployment`
- `reload_server`

### ローカル Tool

Teams 通知は MCP にしません。

`src/jboss_agent/local_tools/teams.py` に `@tool` で `send_teams_alert` を実装し、LangGraph の `ToolNode` で実行します。

これにより、1つのプロジェクト内で

- LangGraph のローカル Tool
- MCP Tool

の違いを学べます。

## 開発環境

推奨: VS Code + Dev Containers + Docker Desktop

### 1. 展開

ZIP を展開して VS Code でフォルダを開きます。

### 2. 環境変数

```bash
cp .env.example .env
```

`.env` に最低限以下を設定します。

```env
GOOGLE_API_KEY=your_gemini_api_key
TEAMS_WEBHOOK_URL=your_teams_workflow_webhook_url
```

`.env` は Git 管理しません。Docker イメージにも埋め込みません。

### 3. Dev Container

VS Code のコマンドパレットから:

```text
Dev Containers: Reopen in Container
```

### 4. 依存確認

コンテナ内で:

```bash
python --version
python -c "import langgraph; print('langgraph ok')"
python -c "import streamlit; print('streamlit ok')"
```

## 実装開始方法

このスターターパックには、実装を別AIに依頼するためのプロンプトを用意しています。

- `docs/SPECIFICATION.md` : 完成形の仕様
- `docs/ARCHITECTURE.md` : アーキテクチャ・責務分離
- `docs/LEARNING_ROADMAP.md` : 段階実装の順番
- `docs/IMPLEMENTATION_PROMPT.md` : 別AIへそのまま渡す実装プロンプト
- `docs/ACCEPTANCE_TESTS.md` : 完了条件

別AIには、まず `docs/IMPLEMENTATION_PROMPT.md` の「マスタープロンプト」を貼り、必要に応じてこのZIPも添付してください。

## 重要な設計原則

1. LLM に何でもやらせない
2. ルーティング可能な判断と、決定論的な制御を分離する
3. write 系 MCP Tool は承認前の Agent には公開しない
4. Tool の境界を明確にする
5. `graph/` を見れば LangGraph の学習内容が分かる構造にする
6. JBoss 固有処理は `jboss/`、MCP は `mcp_client/`、通知は `local_tools/` に分ける
7. Scheduler は LangGraph の外に置く
8. Fake JBoss をデフォルトにし、後から Real JBoss に差し替え可能にする

## Teams Webhook について

2026年時点では、旧 Microsoft 365 / Office 365 Connector の新規利用ではなく、Teams の Workflows で「Teams Webhook 要求が受信されたとき」を使う構成を前提にします。

アプリ側は `TEAMS_WEBHOOK_URL` に HTTPS POST するだけにし、Teams 固有の認証・投稿処理を `send_teams_alert` Tool 内に閉じ込めます。

## Gemini

LangChain の `ChatGoogleGenerativeAI` を利用します。

`GOOGLE_API_KEY` を `.env` に設定し、モデル名は `GEMINI_MODEL` で変更できるようにします。

## 最初に作るべきもの

いきなり全部実装しないでください。

最初は `LEARNING_ROADMAP.md` の STEP 0 から始め、各 STEP で:

- 何を学ぶか
- なぜその設計なのか
- 何を LangGraph に任せるか
- 何を通常の Python に任せるか

を説明しながら実装してください。

---

## STEP 0 — Environment（実装済み）

STEP 0 では LangGraph の Graph 本体はまだ作っていません。まず、後続 STEP が同じ環境・同じ設定方式で動くための土台だけを実装しています。

### 追加されたもの

- `src/jboss_agent/config.py`
  - `.env` / 環境変数を `pydantic-settings` で読み込み
  - 型・範囲を検証
  - Secret をコードに直書きしない
- `src/jboss_agent/llm/gemini.py`
  - `ChatGoogleGenerativeAI` の生成
  - Gemini への1回の疎通確認
- `src/jboss_agent/cli/gemini_ping.py`
  - CLI から疎通確認
- `src/jboss_agent/ui/streamlit_app.py`
  - STEP 0 用 Hello World 画面
- 設定・Gemini helper・Streamlit entrypoint の基本テスト

### 開始手順

1. `.env.example` を `.env` にコピーします。

```bash
cp .env.example .env
```

Windows PowerShell の場合:

```powershell
Copy-Item .env.example .env
```

2. `.env` の `GOOGLE_API_KEY` に Google AI Studio の API key を設定します。

```env
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

3. VS Code でこのフォルダを開き、次を実行します。

```text
Dev Containers: Reopen in Container
```

4. コンテナ内で確認します。

```bash
python --version
python -c "import langgraph; print('langgraph ok')"
python -c "import streamlit; print('streamlit ok')"
```

5. テストを実行します。

```bash
make test
```

6. Gemini に1回問い合わせます。

```bash
make gemini-ping
```

成功例:

```text
model=gemini-3.5-flash
response=GEMINI_CONNECTION_OK
```

7. Streamlit を起動します。

```bash
make app
```

VS Code が転送した `8501` ポートをブラウザで開いてください。

### STEP 0 でまだ作らないもの

- LangGraph State
- Node / Edge
- Conditional Edge
- Tool / ToolNode
- MCP Server / Client
- Human-in-the-loop
- Scheduler
- JBoss simulator

これらは `docs/LEARNING_ROADMAP.md` の順に STEP 1 以降で追加します。

---

## STEP 1 — LangGraph Core（実装済み）

最小の Graph API を実装しています。

```text
START -> collect_fake_log -> simple_check -> END
```

実行:

```bash
make step1
```

主なファイル:

```text
src/jboss_agent/graph/state.py
src/jboss_agent/graph/core_graph.py
src/jboss_agent/graph/nodes/collect_fake_log.py
src/jboss_agent/graph/nodes/simple_check.py
```

ここでは LLM を使いません。State / Node / Edge / `compile()` / `invoke()` の動きだけを確認できます。

---

## STEP 2 — LLM Routing（実装済み）

STEP 1 の固定 Edge と比較するため、Gemini の Structured Output と Conditional Edge を使う Graph を別に残しています。

```text
START
  -> collect_fake_log
  -> analyze_logs
  -> Conditional Edge
       NORMAL          -> normal_branch
       THREAD_POOL     -> thread_pool_branch
       DATASOURCE_POOL -> datasource_pool_branch
       DEPLOYMENT      -> deployment_branch
       UNKNOWN         -> unknown_branch
  -> END
```

Gemini からは自由文ではなく、Pydantic の `LogClassification` に対応する JSON Schema で以下を受け取ります。

```text
incident_detected
category
confidence
summary
evidence
```

実行:

```bash
make step2
```

デフォルトは thread pool らしい raw log を入力します。

```bash
make step2 SCENARIO=normal
make step2 SCENARIO=thread_pool
make step2 SCENARIO=datasource_pool
make step2 SCENARIO=deployment
make step2 SCENARIO=unknown
```

`SCENARIO` は CLI が raw log sample を選ぶためだけに使用し、Graph State や Gemini prompt に正解ラベルは渡しません。

詳しい学習ポイントは:

```text
docs/STEP1_STEP2_GUIDE.md
```

を参照してください。

### STEP 2 の責務分担

```text
Gemini
  ログの意味を解釈して category を決める

LangGraph
  State を運び、Node と Conditional Edge を実行する

通常の Python
  category -> 次 Node の対応表を保証する
```

Tool / ToolNode / MCP はまだありません。これらは STEP 4 以降で追加します。

### STEP 1 / 2 テスト

```bash
make test
```

STEP 2 の Graph test は FakeClassifier を dependency injection し、Gemini API を呼びません。
これにより Graph のルーティングテストと LLM の実通信を分離しています。

---

## STEP 3 — Monitoring / Cursor（実装済み）

Fake JBoss の `server.log` を byte cursor で差分読みします。

```text
START -> collect_logs
              |
              +-- no delta -> no_new_logs -> END
              |
              +-- delta -> analyze_logs(Gemini) -> category branch -> END
```

実行:

```bash
make step3
```

重要なのは、ログに変化がない回は Gemini を呼ばないことです。

---

## STEP 4 — Local Tool: Teams（実装済み）

Teams 通知をローカル LangChain Tool として実装しています。

```text
Gemini
  -> tool_calls: send_teams_alert
  -> tools_condition
  -> ToolNode
  -> local Python Tool
  -> ToolMessage
  -> Gemini
```

デフォルト:

```env
TEAMS_DRY_RUN=true
```

なので Webhook URL がなくても試せます。

```bash
make step4
```

実送信する場合のみ:

```env
TEAMS_DRY_RUN=false
TEAMS_WEBHOOK_URL=https://...
```

---

## STEP 5 — MCP Read Tools（実装済み）

Fake JBoss を stdio MCP Server として別プロセスで起動し、`langchain-mcp-adapters` で read-only Tool を取得します。

```text
LangGraph
  -> ToolNode
  -> LangChain MCP Tool
  -> stdio
  -> Fake JBoss MCP Server
  -> Fake JBoss file-backed state
```

実行:

```bash
make step5
```

MCP Inspector を使いたい場合:

```bash
make mcp-dev
```

STEP 8 まで進んだ現在、MCP Server 自体は read/write の両 capability を公開します。ただし STEP 5/6 のクライアントは **read-only subset だけをフィルタして取得**するため、調査Agentに write Tool は見えません。

```text
read_server_log
get_server_health
get_thread_pool_status
get_datasource_status
get_deployment_status
get_recent_config_changes
```

`execute_jboss_cli` / `execute_shell` のような任意実行 Tool は STEP 9 時点でも作っていません。

詳しい比較は:

```text
docs/STEP3_STEP4_STEP5_GUIDE.md
```

を参照してください。

### STEP 3〜5 一括確認

```bash
make test
make step3
make step4
make step5
```

STEP 3 / STEP 4 は Gemini API を利用します。STEP 5 は Gemini API を使わず、MCP 接続だけを確認します。


---

## STEP 6 — Agentic Investigation（実装済み）

ここで初めて、LLM が **次にどの read-only MCP Tool を使うか**を選びます。

```text
START
  -> prepare_investigation
  -> investigate (Gemini + read-only tools)
       | tool_calls
       v
     ToolNode(read MCP tools)
       -> record_tool_evidence
       -> investigate
       |
       | no tool call / investigation limit
       v
     diagnose (Structured Output)
  -> END
```

実行:

```bash
make step6
```

重要な境界:

```text
Gemini: 何を追加調査するか決める
LangGraph: Tool loop と最大調査回数を管理する
MCP: JBoss の read capability を提供する
Python: write Tool を investigation model に渡さない
```

---

## STEP 7 — Human-in-the-loop（実装済み）

対処案を通常 Python の Risk Policy で検証した後、write 操作前に `interrupt()` します。

```text
validate_proposed_action
  -> BLOCKED -> END
  -> approval interrupt
       ↓ same thread_id
Command(resume={...})
       ↓
approved / rejected / edited+approved
```

通常デモ:

```bash
make step7
```

SQLite で「別プロセスから同じ thread_id を再開」を確認する場合:

```bash
make step7-pause
make step7-resume
```

`step7-pause` は pending approval のままプロセスを終了します。`step7-resume` は同じ `incident:step7-durable-demo` を SQLite から復元して再開します。

> `interrupt()` より前のコードは resume 時に再実行されます。そのため approval Node の interrupt 前には HTTP POST や write Tool などの副作用を置いていません。

---

## STEP 8 — MCP Write Tools（実装済み）

承認済み Action を Python が明示的な write MCP Tool に変換します。

```text
approval_status=APPROVED
  -> validate again
  -> prepare_write_call (Python)
  -> ToolNode(write MCP tools)
  -> capture_write_result
  -> END
```

実行:

```bash
make step8
```

公開 capability:

```text
set_thread_pool_max_threads      1..200
set_datasource_max_pool_size     1..200
restart_deployment
reload_server
```

**Gemini に write Tool を自由選択させない**のがポイントです。

---

## STEP 9 — Recovery Loop（実装済み）

STEP 6〜8 を1本の Incident Response Graph に接続し、変更後に read-only MCP Tool で復旧確認します。

```text
investigate
  -> diagnose
  -> risk policy
  -> interrupt approval
  -> write MCP
  -> verify recovery
       | Recovered
       +-----------> END
       |
       | Not recovered
       v
  prepare_retry
       -> investigate

MAX_RECOVERY_ATTEMPTS 到達
       -> fail_safe -> END
```

実行:

```bash
make step9
```

CLI デモでは approval payload を表示した後、自動で approve して続きを流します。UI で人がボタンを押す実装は STEP 11 です。

詳しいコード対応と State の変化は:

```text
docs/STEP6_STEP7_STEP8_STEP9_GUIDE.md
```

を参照してください。

### STEP 6〜9 一括確認

```bash
make test
make step6
make step7
make step8
make step9
```

この時点で Incident Response 側は、**自律調査 / HITL / write capability / 復旧ループ**まで揃っています。次の STEP 10 は Graph の外から定期起動する Scheduler です。
