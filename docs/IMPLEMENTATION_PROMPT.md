# 別AIへ渡す実装プロンプト

以下の「マスタープロンプト」を新しいAIチャットへそのまま貼ってください。

このZIPをアップロードできる場合は同時に添付し、AIにこのリポジトリを直接編集させるのが最も簡単です。

---

# マスタープロンプト

あなたには、このリポジトリにある仕様に従って **LangGraph JBoss Incident Response Agent** を段階的に実装してもらいます。

このプロジェクトの第一目的は「JBoss 運用自動化製品の完成」ではなく、**私が LangGraph を自由に扱えるようになること**です。

私は Java には慣れていますが、Python / LangGraph は学習中です。そのため、コードを一気に生成するだけではなく、各 STEP で以下を短く明確に説明してください。

1. 今回学ぶ LangGraph の概念
2. State のどの値がどう変化するか
3. Node は何を担当するか
4. Edge / Conditional Edge はなぜそこに必要か
5. LLM に任せている判断は何か
6. Python の通常ロジックで制御している部分は何か
7. Tool と MCP の境界は何か

## 必ず読むファイル

実装前に次を読んでください。

- `README.md`
- `docs/SPECIFICATION.md`
- `docs/ARCHITECTURE.md`
- `docs/LEARNING_ROADMAP.md`
- `docs/ACCEPTANCE_TESTS.md`

仕様と異なる設計に変更したい場合は、勝手に大きく変えず、理由を説明してください。

## 技術方針

- Python
- LangGraph Graph API を明示的に使う
- Gemini (`ChatGoogleGenerativeAI`)
- Streamlit
- MCP は JBoss capability 用
- Teams 通知は MCP にせず、LangChain/LangGraph のローカル Tool として `@tool` で実装
- `ToolNode` と `tools_condition` を学習できる実装を含める
- Human-in-the-loop は `interrupt()` と `Command(resume=...)` を使う
- Scheduler は Graph の外
- Dev Containers で動作
- Secret は `.env` から取得
- `.env` は Git 管理しない
- Fake JBoss をデフォルトにする
- 実 JBoss は後から差し替えられる設計

## 特に重要な Tool 境界

### Local Tool

Teams 通知:

```text
send_teams_alert(...)
```

これはローカル Python Tool として実装してください。

### MCP Tool

JBoss:

```text
read_server_log
get_server_health
get_thread_pool_status
get_datasource_status
get_deployment_status
get_recent_config_changes
set_thread_pool_max_threads
set_datasource_max_pool_size
restart_deployment
reload_server
```

### 禁止

以下は作らないでください。

```text
execute_jboss_cli(command: str)
execute_shell(command: str)
```

LLM に任意コマンド実行権限を与えないでください。

## Agent の前提

Fault Injector がどの障害を入れたかは Agent に絶対に教えないでください。

Agent は:

1. ログ増分を見る
2. 障害有無を推定
3. 必要なら read-only MCP Tool を自分で選んで追加調査
4. 原因推定
5. 対処案生成
6. Human approval
7. write MCP Tool
8. recovery verification

の順で動きます。

正常ログのみ増えるケースも必ず作ってください。

## 実装の進め方

`docs/LEARNING_ROADMAP.md` の STEP を **1つずつ** 実装してください。

一度に全 STEP を完成させないでください。

最初は STEP 0 から開始してください。

各 STEP で:

1. 変更するファイル一覧を示す
2. 実装する
3. テストを追加する
4. 実行コマンドを示す
5. 実行結果を確認する
6. 今回の LangGraph の学習ポイントを説明する
7. 次 STEP へ進む前に、今回の状態を簡潔にまとめる

## 実装品質

- 型ヒントを付ける
- Pydantic / TypedDict を適切に使う
- 1ファイルに責務を詰め込みすぎない
- Graph 定義と業務ロジックを分離する
- Prompt 文字列を巨大な Node 関数に直書きしない
- Tool の description を明確にする
- write 操作は validation を必須にする
- retry 上限を設ける
- Tool side effect を可能な限り idempotent にする
- ログを出す
- テスト可能な構造にする

## Dev Container

このプロジェクトは Windows / macOS / Linux のホスト差を小さくするため、Dev Container を標準開発環境とします。

`Dockerfile` / `.devcontainer/devcontainer.json` / `pyproject.toml` を壊さず、誰でも以下で開始できるようにしてください。

```text
1. ZIP 展開
2. .env.example -> .env
3. GOOGLE_API_KEY を設定
4. Dev Containers: Reopen in Container
5. コマンドを実行
```

## Teams

Teams の URL は:

```env
TEAMS_WEBHOOK_URL=
```

から取得してください。

初期実装では:

```env
TEAMS_DRY_RUN=true
```

をサポートし、Webhook がなくても学習を進められるようにしてください。

## Gemini

```env
GOOGLE_API_KEY=
GEMINI_MODEL=
```

から取得してください。

Google AI Studio の API key を使う前提です。

## 最初の依頼

まず `STEP 0 — Environment` を実装してください。

この STEP では LangGraph の本体ロジックはまだ作り込まず、Dev Container、依存関係、設定読込、Gemini 疎通、Streamlit Hello World、基本テストまでにしてください。

完了したら、私が「STEP 1へ」と言える状態にしてください。

---

# STEP 継続用の短いプロンプト

新しいチャットへ途中状態を渡す場合は、リポジトリを添付して次を使ってください。

```text
このリポジトリは LangGraph JBoss Incident Response Agent の学習用プロジェクトです。

最初に以下を読んでください。
- README.md
- docs/SPECIFICATION.md
- docs/ARCHITECTURE.md
- docs/LEARNING_ROADMAP.md
- docs/ACCEPTANCE_TESTS.md

既存コードと git diff を確認し、現在どの STEP まで完了しているか判断してください。
完了済み STEP を壊さず、次の未完了 STEP だけ実装してください。

このプロジェクトの目的は LangGraph の学習なので、実装後に State / Node / Edge / LLM / Tool / MCP の役割を今回の STEP に即して説明してください。
```
