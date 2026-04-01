# FinGuard: Autonomous Financial Audit & Compliance Environment

FinGuard is a robust, lightweight evaluation environment built on the **OpenEnv** standard, commanding an LLM agent to accurately act as a corporate auditor handling adversarial test cases.

## The "Adversarial Design"
This environment specifically features high-noise variables and **Date Traps** to strictly test if language models are hallucination-prone. 
Agents must prove their competence by catching subtle, off-by-one discrepancies (e.g., April 5th vs April 6th) instead of lazily resolving valid-looking strings to identical amounts.

## Risk-Averse RL Function
The internal scoring system prioritizes **Safe Refusal** over **Reckless Matching**. The agent is rewarded (+0.8 points) for correctly mapping anomalies to an `escalate` label, ensuring human operators intercept policy violations rather than blindly trusting automated assumptions.

## Infrastructure Resilience
Our baseline deployment (contained in `inference.py`) includes a robust try-except loop implementing an **Exponential Backoff**. This was a necessary real-world layer added to process the evaluation state gracefully through heavy 503 Service Unavailable API backend spikes without corrupting the transaction sequence!

---

### Observation Space
The memory footprint is heavily minimized to sub-8GB constraints by injecting only necessary local fields into the observation payload via a `FinGuardObservation` Pydantic model:
- `current_transaction`: Defines the Date, Amount, noisy Vendor string, and Description.
- `list_of_available_receipts`: Array of unassigned `Receipt` objects.
- `policy_text`: The mandatory policy logic bounds.
- `transactions_remaining`: Count metric for LLM tracking.
- `done`: Episode terminal flag.

### Action Space
Agents must output strict structured JSON corresponding to the `FinGuardAction` model:
- `action_type`: `"match"`, `"flag_missing"`, or `"escalate"`.
- `transaction_id`: Mapped ID.
- `receipt_id`: Accompanying ID (if match is chosen).
- `reason`: Internal monologue/justification (if escalate is chosen).

## Baseline Score 
A test executing against the `gemini-3-flash-preview` model yielded the following baseline validation:
**Final Simulated Score: 4.4 / 5.0**
