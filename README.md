# LangGraph JBoss Incident Response Agent — Starter Pack

このリポジトリは、LangGraph を「実際に動く題材」で学ぶためのスターターパックです。

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

最初は `LEARNING_ROADMAP.md` の STEP 1 から始め、各 STEP で:

- 何を学ぶか
- なぜその設計なのか
- 何を LangGraph に任せるか
- 何を通常の Python に任せるか

を説明しながら実装してください。
