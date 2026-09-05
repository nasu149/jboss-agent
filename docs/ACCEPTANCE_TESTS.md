# Acceptance Tests

## A. Monitoring

### A-1 No changes

Given:
- previous cursor == current cursor

Expected:
- LLM is not invoked
- Incident is not created
- Teams notification is not sent

### A-2 Normal log increase

Given:
- INFO level activity only

Expected:
- Gemini returns `incident_detected=false`
- Incident is not created

### A-3 Abnormal log increase

Given:
- thread exhaustion-like logs

Expected:
- Gemini returns `incident_detected=true`
- Incident ID is created
- Teams local Tool is executed once

---

## B. Local Teams Tool

### B-1 Dry run

Given:

```env
TEAMS_DRY_RUN=true
```

Expected:
- no external POST
- payload is logged
- Tool returns success

### B-2 Real webhook

Given:
- valid `TEAMS_WEBHOOK_URL`

Expected:
- POST succeeds
- duplicate invocation for same incident does not double-send

---

## C. Incident Investigation

### C-1 Thread Pool

Ground Truth:

```text
max_threads changed from 80 to 20
active=20
queue>0
CPU<60%
```

Expected:
- Agent calls relevant MCP read tools
- Agent diagnoses thread pool issue
- Agent proposes 20 -> 80

### C-2 Datasource

Expected:
- Agent calls datasource tool
- Does not unnecessarily change thread pool

### C-3 Normal

Expected:
- no remediation

---

## D. HITL

### D-1 Approve

Expected:
- Graph pauses
- Same thread_id resumes
- write Tool executes only after approval

### D-2 Reject

Expected:
- write Tool is never executed
- Incident closes or escalates

### D-3 Edit

Human changes proposed value.

Expected:
- edited value is validated
- valid value executes
- invalid value is blocked

---

## E. Recovery

### E-1 Success

Expected:
- post-change health check passes
- Incident reaches END

### E-2 Failure

Expected:
- Graph loops back to investigation
- maximum retry count prevents infinite loop

---

## F. Persistence

Expected:
- pending approval survives application restart when durable checkpointer is enabled
- monitoring cursor is restored for `monitor:jboss-01`

---

## G. Fault Simulator Isolation

Expected:
- Ground Truth is stored outside Agent-visible State
- Agent prompt does not contain injected fault type
- UI reveals Ground Truth only after completion or explicit debug mode
