# STEP 1 / STEP 2 学習ガイド

この2 STEPは並べて見ると LangGraph の役割が分かりやすい。

## STEP 1 — LangGraph Core

Graph:

```text
START
  -> collect_fake_log
  -> simple_check
  -> END
```

### State

`CoreLearningState` は Node 間で受け渡す共有データ。

```text
input_log_lines       CLIなどから入る任意のログ
log_text              collect_fake_log が作る
simple_check_result   simple_check が作る
node_trace            どのNodeを通ったか
```

Node は State 全体を直接書き換えるのではなく、**更新したいキーだけ dict で返す**。
LangGraph がその更新を次の State に反映する。

### Node

`collect_fake_log` は決定論的な Python 処理。
LLM に「ログを集めるべき？」とは聞かない。

`simple_check` も通常の Python で `WARN / ERROR / FATAL` を見るだけ。
これはわざと単純にしてあり、STEP 2 との比較材料になる。

### Edge

STEP 1 の Edge は全部固定。

```python
builder.add_edge(START, "collect_fake_log")
builder.add_edge("collect_fake_log", "simple_check")
builder.add_edge("simple_check", END)
```

つまり実行順はコードで100%決まる。

### compile / invoke

`StateGraph(...)` は設計図。
`compile()` で実行可能な Graph にする。
`invoke(initial_state)` で1回の Graph 実行を開始する。

---

## STEP 2 — LLM Routing

Graph:

```text
START
  -> collect_fake_log
  -> analyze_logs (Gemini Structured Output)
  -> Conditional Edge
       NORMAL          -> normal_branch
       THREAD_POOL     -> thread_pool_branch
       DATASOURCE_POOL -> datasource_pool_branch
       DEPLOYMENT      -> deployment_branch
       UNKNOWN         -> unknown_branch
  -> END
```

## Structured Output

Gemini に自由文だけを返させず、`LogClassification` の JSON Schema に合わせる。

```text
incident_detected
category
confidence
summary
evidence
```

`category` は次の5種類だけ。

```text
NORMAL
THREAD_POOL
DATASOURCE_POOL
DEPLOYMENT
UNKNOWN
```

Pydantic が LLM の返却値を検証するので、例えば `CPU` のような未定義カテゴリは通らない。

## LLM と Python の責務分担

### Gemini に任せる

```text
このログは何を意味しているか？
THREAD_POOL と DATASOURCE_POOL のどちらっぽいか？
根拠は何か？
```

これは曖昧な意味解釈なので LLM 向き。

### Python / LangGraph に任せる

```text
THREAD_POOL なら thread_pool_branch へ行く
NORMAL なら normal_branch へ行く
```

この対応表は決定論的なルールなので LLM に決め直させない。

つまり:

```text
Gemini = 意味を判断する
LangGraph = 判断結果を使って状態遷移する
Python = ルーティング規則を保証する
```

## なぜ Conditional Edge なのか

STEP 1 は常に同じ次 Node だった。
STEP 2 は `analyze_logs` の結果によって次 Node が変わる。

そのため:

```python
builder.add_conditional_edges("analyze_logs", route_by_category)
```

を使う。

`route_by_category(state)` は State の `category` を見て、次に実行する Node 名を返す。

## Tool / MCP はまだない

STEP 2 で Gemini を呼んでいるが、これは **Tool Calling ではない**。
単に Node の中から LLM を1回呼んで Structured Output を受け取っているだけ。

```text
STEP 2:
Node -> Gemini -> Structured Output -> State
```

後の STEP 4/5 では:

```text
Gemini -> Tool Call -> ToolNode / MCP -> Result
```

を学ぶ。

## 実行

STEP 1:

```bash
make step1
```

STEP 2:

```bash
make step2
```

別サンプル:

```bash
make step2 SCENARIO=normal
make step2 SCENARIO=datasource_pool
make step2 SCENARIO=deployment
make step2 SCENARIO=unknown
```

`SCENARIO` というラベルは CLI が raw log を選ぶためだけに使う。
Graph / Gemini に渡すのは raw log lines だけで、正解ラベルは渡さない。

## テスト

```bash
make test
```

STEP 2 の Graph テストでは Gemini API を呼ばず、FakeClassifier を注入する。
これにより **Conditional Edge 自体の正しさ** と **外部LLMの精度** を分離してテストできる。
