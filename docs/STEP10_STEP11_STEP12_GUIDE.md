# STEP 10 / 11 / 12 Guide

この3 STEP で、STEP 0〜9 で作った「単発の Incident Response Graph」を、
**定期監視され、人がUIから承認でき、最後に数字で評価できる教材システム**へ接続します。

---

# STEP 10 — Scheduler

## 1. 今回学ぶこと

- Scheduler と LangGraph workflow の責務分離
- fixed monitoring `thread_id`
- Checkpointer を cursor persistence に使う意味
- 定期処理の中に `sleep()` を書かない設計

## 2. 最終的な流れ

```text
APScheduler
    |
    | every POLL_INTERVAL_SECONDS
    v
OperationalAgentService.run_monitoring_cycle()
    |
    v
Monitoring Graph
    START
      -> start_monitoring_cycle
      -> collect_logs        -- deterministic MCP read_server_log
      -> new logs?
           No  -> commit_cursor -> END
           Yes -> analyze_logs (Gemini Structured Output)
                    -> incident?
                         No  -> commit_cursor -> END
                         Yes -> create_incident
                              -> notify_teams_local_tool
                              -> commit_cursor
                              -> END
    |
    | incident detected
    v
Incident Response Graph (STEP 9)
    -> read-only investigation
    -> diagnosis
    -> risk policy
    -> interrupt()  ← Schedulerはここで止めたままにする
```

Scheduler は Incident の中身を判断しません。

```text
Scheduler の責務
= 「いつ起動するか」だけ
```

判断は Graph / Gemini / Domain Logic に残します。

## 3. なぜ固定 thread_id なのか

Monitoring は Incident と違って、サーバごとに1本の継続した監視です。

```text
monitor:jboss-01
```

を毎回再利用します。

Operational Monitoring State では scan の最後に:

```text
current_log_cursor
      ↓
previous_log_cursor
```

を `commit_cursor` Node で保存します。

そのため次回 Scheduler 起動時は、同じ `thread_id` の Checkpoint から cursor を復元できます。

```text
1回目
previous=0
current=1200
commit -> previous=1200

2回目
same thread_id
previous=1200
current=1470

Geminiへ渡すのは1200〜1470だけ
```

## 4. State / Node / Edge

### State

STEP 10 で追加した主な値:

```text
scan_from_cursor
previous_log_cursor
current_log_cursor
new_log_lines
incident_detected
incident_id
teams_notified
```

### Node

`collect_logs` は LLM Node ではありません。

```text
read_server_log(server_id, cursor)
```

を明示的に呼ぶ deterministic Node です。

3分ごとにログを取得するかどうかは曖昧な判断ではないためです。

### Conditional Edge

```text
new logs?
incident detected?
```

だけを条件分岐にしています。

## 5. 実行

1回だけ確認:

```bash
make step10-once
```

Schedulerを継続起動:

```bash
make step10
```

デモでは `.env` を:

```env
POLL_INTERVAL_SECONDS=10
```

などにすると確認しやすいです。

---

# STEP 11 — Streamlit UI

## 1. 今回学ぶこと

- Graph と UI を直接混ぜない
- pending interrupt の外部表示
- `Command(resume=...)` をUI操作へ接続する
- Agent-visible State と Ground Truth を分離する

## 2. 3種類の「保存領域」を分ける

ここは非常に重要です。

```text
1. LangGraph Checkpointer
   GraphそのもののState
   - monitoring cursor
   - messages
   - pending interrupt
   - approval前のproposed_action

2. Runtime SQLite
   UI表示用メタデータ
   - last scan
   - next scan
   - incident一覧
   - activity timeline

3. Simulator Ground Truth SQLite
   Agentが絶対に見てはいけない正解
   - THREAD_POOL_CONFIGURATION
   - DATASOURCE_POOL_EXHAUSTION
   - DEPLOYMENT_FAILURE
   - NORMAL_ACTIVITY
```

Ground Truth は Incident State に入りません。

## 3. Approval UI

Graph が:

```python
interrupt(payload)
```

で止まると、Runtime Store には approval payload の表示用コピーを保存します。

Streamlit はそれを表示するだけです。

```text
Current value: 20
Proposed value: 80
Risk: MEDIUM
Reason: ...

[Approve]
[Reject]
[Edit & Approve]
```

Approve ボタンは write Tool を直接呼びません。

```text
Streamlit button
   ↓
OperationalAgentService.resume_incident()
   ↓
Command(resume={"decision": "approve"})
   ↓
same incident thread_id
   ↓
approval Node 再開
   ↓
Python validation
   ↓
write MCP Tool
```

UIから直接JBoss変更しないのがポイントです。

## 4. Fault injection

通常UIでは:

```text
[Inject Random Event]
```

だけを押します。

内部では4種類からランダムに選びますが、Agentには正解を渡しません。

```text
FaultInjector
     ↓
Fake JBoss state/logs を変更

GroundTruthStore
     ↓
正解ラベルを別DBへ保存
```

Agentが見るもの:

```text
server.log
MCP read Tool の結果
```

Agentが見ないもの:

```text
Ground Truth scenario
```

## 5. Ground Truth reveal

障害イベント:

```text
Incident workflow終了後のみ表示
```

正常イベント:

```text
Monitoring scan終了後のみ表示
```

これにより診断中に正解が漏れません。

## 6. 実行

Terminal 1:

```bash
make step10
```

Terminal 2:

```bash
make step11
```

ブラウザで:

```text
Inject Random Event
   ↓
Scheduler待ち or Run scan now
   ↓
Agent investigation
   ↓
Approval
   ↓
Approve
   ↓
Recovery
   ↓
Ground Truth comparison
```

を確認できます。

---

# STEP 12 — Evaluation

## 1. 今回学ぶこと

Agent は「1回うまく動いた」だけでは評価できません。

STEP 12 では10〜30回イベントを流します。

```text
Fault Injector
   ↓
Monitoring Graph
   ↓
Incident detection
   ↓
Incident Agent
   ↓
MCP investigation
   ↓
Diagnosis
   ↓
Auto Approve for evaluation
   ↓
Write MCP
   ↓
Recovery verification
   ↓
Metrics
```

評価条件を揃えるため、Human approval は評価時だけ自動Approveします。

これは本番フローからHITLを消したわけではありません。
UIデモでは引き続き人が承認します。

## 2. ランダムイベント

候補:

```text
THREAD_POOL_CONFIGURATION
DATASOURCE_POOL_EXHAUSTION
DEPLOYMENT_FAILURE
NORMAL_ACTIVITY
```

完全な乱数だけだと10回の試験で一部シナリオが一度も出ないことがあります。

そのためSTEP 12では:

```text
4 scenarioをshuffle
4 scenarioをshuffle
...
```

として、全種類を混ぜながらランダム順序にしています。

`EVALUATION_SEED` で再現可能です。

## 3. 指標

### Incident detection accuracy

```text
障害 → incident作成
正常 → incidentを作らない
```

の正解率。

### False Positive count

```text
NORMAL_ACTIVITY
なのに
incident_detected=true
```

の件数。

### False Negative count

```text
本当は障害
なのに
incidentが作られない
```

の件数。

### Diagnosis accuracy

Ground Truth と Agent の root cause を比較します。

評価コード:

```text
THREAD_POOL_CONFIGURATION
DATASOURCE_POOL_EXHAUSTION
DEPLOYMENT_FAILURE
```

### Recovery success rate

本当の障害シナリオのうち、最終的に:

```text
recovered=true
```

になった割合。

### Average investigation Tool calls

write Tool は含めず、LLM が選んだ **read-only MCP Tool call** だけを数えます。

## 4. Teamsは評価時に送らない

`.env` が万一:

```env
TEAMS_DRY_RUN=false
```

でも、STEP 12 の10〜30回評価から実Teamsへ大量通知しないよう、Evaluation専用 notifier をdependency injectionしています。

これはOperational Graphのテスト可能性を高める例でもあります。

## 5. 実行

デフォルト:

```bash
make step12
```

評価は同じ Fake JBoss を繰り返しresetするため、**`make step10` のSchedulerを停止してから**実行してください。

回数とseed変更:

```bash
make step12 EVAL_RUNS=20 EVAL_SEED=123
```

範囲:

```text
10 <= EVAL_RUNS <= 30
```

結果:

```text
.data/evaluation_latest.json
```

Streamlit の最下部にも最新summaryを表示します。

---

# STEP 10〜12 の責務分担

| Component | Responsibility |
|---|---|
| APScheduler | 何秒ごとに起動するか |
| Monitoring Graph | cursor差分取得、解析、incident検知 |
| Gemini classifier | logの意味解釈 |
| Local Teams Tool | 通知side effect |
| Incident Graph | 調査、診断、HITL、復旧loop |
| Gemini investigation agent | 次に使うread Tool選択 |
| MCP | JBoss capability |
| Python Domain Logic | risk/validation/write mapping/recovery条件 |
| Checkpointer | Graph State / interrupt / cursor persistence |
| Runtime Store | Dashboard表示用状態 |
| Fault Injector | Fake JBossへイベント注入 |
| Ground Truth Store | Agentから隔離された正解 |
| Streamlit | 可視化・Human resume |
| Evaluation Runner | 複数trial実行とmetrics集計 |

---

# ここまで来ると何が完成したか

STEP 0〜12 で、次の主要要素を一通り触れます。

```text
State
Node
Edge
Conditional Edge
Structured Output
Tool Calling
ToolNode
MCP
Agentic Tool Selection
MessagesState
Checkpointer
thread_id
interrupt
Command(resume)
Loop
Scheduler
UI
Evaluation
```

残る STEP 13 は Optional です。

```text
Fake JBoss Adapter
      ↓ 差し替え
Real JBoss Adapter
```

Agent / Graph を大きく変えず、MCP Server内部の実装境界を交換する段階です。
