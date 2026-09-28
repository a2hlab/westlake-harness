#!/usr/bin/env python3
"""Materialize the accepted Fn03/R1 Action contracts and design specifications."""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

COMMON_PRECONDITIONS = [
    "Fn03 Concept Bridge Contract is accepted with R1 as the primary route.",
    "The input carries an authenticated owner, process_epoch, generation and transition_id.",
    "The accepted lifecycle mapping_version is fn03-lifecycle-mapping-v1.",
]

MAPPING_SCHEMA = {
    "schema_version": "fn03-lifecycle-mapping-v1",
    "mapping_version": "fn03-lifecycle-mapping-v1",
    "unknown_policy": "REJECT_UNSUPPORTED_STATE_BEFORE_CALLBACK",
    "explicit_rejections": [
        {
            "source": "STOPPED",
            "oh_target": "INITIAL",
            "ingress": "OH_INITIATED",
            "reason": "UNSUPPORTED_OH_INITIATED_TERMINATION_V1",
            "owner": "outside Fn03.A05 Android-finish scope; requires future contract revision",
        },
        *[
            {
                "source": source,
                "oh_target": "INITIAL",
                "ingress": "ANDROID_FINISH",
                "reason": "UNSUPPORTED_ANDROID_FINISH_SOURCE_STATE_V1",
                "owner": "Fn03.A05 v1 supports only CREATED",
            }
            for source in ("RESUMED", "PAUSED", "STOPPED")
        ],
    ],
    "transitions": [
        {
            "source": "REGISTERED",
            "oh_target": "LAUNCH",
            "android_transactions": ["LaunchActivityItem"],
            "required_callbacks": ["onCreate"],
            "required_receipts": ["CREATE_TERMINAL"],
            "require_first_frame_effect": "NOT_APPLICABLE",
        },
        {
            "source": "CREATED",
            "oh_target": "FOREGROUND_NEW",
            "android_transactions": ["ResumeActivityItem"],
            "required_callbacks": ["onStart", "onResume"],
            "required_receipts": ["RESUME_TERMINAL"],
            "require_first_frame_effect": "ADD_FOREGROUND_READY_FROM_A10_WHEN_TRUE",
        },
        {
            "source": "PAUSED",
            "oh_target": "FOREGROUND_NEW",
            "android_transactions": ["ResumeActivityItem"],
            "required_callbacks": ["onResume"],
            "required_receipts": ["RESUME_TERMINAL"],
            "require_first_frame_effect": "ADD_FOREGROUND_READY_FROM_A10_WHEN_TRUE",
        },
        {
            "source": "STOPPED",
            "oh_target": "FOREGROUND_NEW",
            "android_transactions": ["ResumeActivityItem"],
            "required_callbacks": ["onRestart", "onStart", "onResume"],
            "required_receipts": ["RESUME_TERMINAL"],
            "require_first_frame_effect": "ADD_FOREGROUND_READY_FROM_A10_WHEN_TRUE",
        },
        {
            "source": "RESUMED",
            "oh_target": "INACTIVE",
            "android_transactions": ["PauseActivityItem"],
            "required_callbacks": ["onPause"],
            "required_receipts": ["PAUSE_TERMINAL"],
            "require_first_frame_effect": "NOT_APPLICABLE",
        },
        {
            "source": "RESUMED",
            "oh_target": "BACKGROUND_NEW",
            "android_transactions": ["PauseActivityItem", "StopActivityItem"],
            "required_callbacks": ["onPause", "onStop"],
            "required_receipts": ["PAUSE_TERMINAL", "STOP_TERMINAL"],
            "transition_identity": "ONE_TRANSITION_ID_TWO_ACTION_RECEIPTS",
            "pause_action_verdict": "A03 ends at PAUSE_TERMINAL with ledger OPEN; it does not require STOP_TERMINAL",
            "closure_owner": "Fn03.A04 closes the transition after STOP_TERMINAL",
            "require_first_frame_effect": "NOT_APPLICABLE",
        },
        {
            "source": "PAUSED",
            "oh_target": "BACKGROUND_NEW",
            "android_transactions": ["StopActivityItem"],
            "required_callbacks": ["onStop"],
            "required_receipts": ["STOP_TERMINAL"],
            "require_first_frame_effect": "NOT_APPLICABLE",
        },
        {
            "source": "FINISH_REQUESTED",
            "oh_target": "INITIAL",
            "android_transactions": ["DestroyActivityItem"],
            "dispatch_owner": "OH INITIAL leg only; finish ingress never dispatches destroy",
            "ordering": "OH INITIAL before HOST_TERMINATE_ACCEPTED enters QUEUED_AWAITING_HOST_ACCEPT and dispatches once only after acceptance",
            "required_callbacks": ["onDestroy"],
            "required_receipts": [
                "HOST_TERMINATE_ACCEPTED",
                "ANDROID_DESTROYED",
                "OH_CLEAN_OR_DEATH",
            ],
            "require_first_frame_effect": "NOT_APPLICABLE",
        },
    ],
}
MAPPING_SCHEMA_TEXT = yaml.safe_dump(MAPPING_SCHEMA, allow_unicode=True, sort_keys=False)
MAPPING_SCHEMA_SHA256 = hashlib.sha256(MAPPING_SCHEMA_TEXT.encode()).hexdigest()

TIMEOUT_POLICY = {
    "schema_version": "fn03-timeout-policy-v1",
    "clock": "monotonic",
    "policies": {
        "terminal_join_timeout": {
            "duration_ms": 5000,
            "start": "first same-generation terminal fact accepted after FINISH_REQUESTED",
            "reason": "TERMINAL_JOIN_TIMEOUT",
            "result_state": "RECONCILE_REQUIRED",
            "guard": "retain capability tombstone and duplicate-prevention state",
        },
        "bind_wait_timeout": {
            "duration_ms": 5000,
            "start": "QUEUED_AWAITING_BIND entry accepted",
            "reason": "BIND_WAIT_TIMEOUT",
            "result_state": "FAILED_TYPED",
            "guard": "never admit the launch after timeout",
        },
        "callback_timeout": {
            "duration_ms": 5000,
            "start": "each dispatch leg key {action_id,transition_id} enters QUEUED",
            "rearm": "each A03 pause leg and A04 stop leg arms its own timer",
            "reason": "CALLBACK_TIMEOUT",
            "result_state": "RECONCILE_REQUIRED",
            "guard": "never synthesize callback or host success",
        },
        "background_leg_gap_timeout": {
            "duration_ms": 5000,
            "start": "A03 PAUSE_TERMINAL accepted while the shared background transition remains OPEN",
            "reason": "BACKGROUND_STOP_LEG_NOT_QUEUED",
            "result_state": "RECONCILE_REQUIRED",
            "guard": "A04 stop leg must enter QUEUED before expiry; no STOPPED success is synthesized",
        },
        "first_frame_timeout": {
            "duration_ms": 5000,
            "start": "DisplayLedger enters AWAITING_FIRST_FRAME",
            "reason": "FIRST_FRAME_TIMEOUT",
            "result_state": "DISPLAY_FAILED",
            "transition_effect": "A07 enters FAILED_TYPED with FIRST_FRAME_NOT_PRESENTED",
            "guard": "never synthesize present or foreground-ready",
        },
        "host_ack_timeout": {
            "duration_ms": 5000,
            "start": "AbilityTransitionDone is sent",
            "reason": "HOST_ACK_TIMEOUT",
            "result_state": "RECONCILE_REQUIRED",
            "guard": "do not resend until reconciliation proves no service-side acceptance",
        },
        "host_terminate_accept_timeout": {
            "duration_ms": 5000,
            "start": "OH terminate request is sent; also covers QUEUED_AWAITING_HOST_ACCEPT",
            "reason": "HOST_TERMINATE_ACCEPT_TIMEOUT",
            "result_state": "RECONCILE_REQUIRED",
            "guard": "do not dispatch destroy; retain capability tombstone and duplicate-prevention state",
        },
    },
}
TIMEOUT_POLICY_TEXT = yaml.safe_dump(TIMEOUT_POLICY, allow_unicode=True, sort_keys=False)
TIMEOUT_POLICY_SHA256 = hashlib.sha256(TIMEOUT_POLICY_TEXT.encode()).hexdigest()

ACTIONS = {
    "A01": {
        "title": "Activity onCreate is dispatched",
        "concept": "Fn03.C01",
        "related": ["Fn03.C02", "Fn03.C03"],
        "kind": "Cr",
        "bits": "1000-0000",
        "capability": "ACTIVITY_CREATE_DISPATCH",
        "intent": "Dispatch one authenticated Activity creation through the stock AOSP ClientTransaction launch path.",
        "scope": "One live Activity instance from admitted launch envelope to a real main-thread onCreate terminal receipt.",
        "trigger": "An admitted launch envelope for a component that is not yet created in the current process epoch.",
        "reads": "launch envelope, application bind state, opaque token registry entry and lifecycle record",
        "writes": "Bridge ActivityLedger REGISTERED→LAUNCH_QUEUED→CREATED with distinct queued/create receipts; stock AOSP alone mutates ActivityClientRecord",
        "positive": "The real target Activity receives onCreate exactly once on the Android main thread through LaunchActivityItem/ActivityThread, and the receipt identifies the same token, generation and transition.",
        "negative": "A duplicate, stale-generation, wrong-owner, missing-component or unbound-process request is rejected without invoking the Activity callback or changing lifecycle state.",
        "failure": "Class load, transaction delivery or callback failure produces a typed terminal failure; CREATED is never published and no success receipt is fabricated.",
        "deps": [
            {"action_id": "Fn02.A02", "reason": "The Android runtime main loop must already be available."},
            {"action_id": "Fn03.A08", "reason": "The launch must resolve a live opaque instance capability."},
            {"action_id": "Fn03.A09", "reason": "A same-generation BOUND receipt and admitted LaunchEnvelope establish the reproducible pre-state."},
        ],
    },
    "A02": {
        "title": "Activity onResume is dispatched",
        "concept": "Fn03.C01",
        "related": ["Fn03.C02", "Fn03.C03"],
        "kind": "Ex",
        "bits": "0000-1000",
        "capability": "ACTIVITY_RESUME_DISPATCH",
        "intent": "Advance one CREATED, PAUSED or STOPPED Activity through the stock AOSP resume transaction; all three v1 edges block final A02 PASS.",
        "scope": "Authenticated foreground transitions from CREATED/PAUSED/STOPPED and the required real callback sequence for the same instance.",
        "trigger": "A foreground transition for a live CREATED/PAUSED/STOPPED Activity; verification uses direct Contract fixtures without A03/A04 verdict inheritance.",
        "reads": "current lifecycle state, transition ledger and opaque token capability",
        "writes": "lifecycle state to RESUMED and a generation-bound resume receipt",
        "positive": "CREATED runs onStart→onResume, PAUSED runs onResume, STOPPED runs onRestart→onStart→onResume on main thread; RESUME_TERMINAL closes only A02, while A07/A10 own later facts.",
        "negative": "Unknown token, illegal predecessor state, stale generation, duplicate transition or wrong owner is rejected with zero callback and zero state mutation.",
        "failure": "Transaction or callback failure leaves no ghost RESUMED state and emits a typed failure tied to the original transition.",
        "deps": [
            {"action_id": "Fn03.A01", "reason": "The verifier needs an independently prepared live Activity pre-state."},
            {"external_gate": "PAUSED_STOPPED_REFERENCE_FIXTURE", "reason": "P03 uses contract reference states, not A03/A04 implementations or verdicts, to avoid a dependency cycle."},
        ],
    },
    "A03": {
        "title": "Activity onPause is dispatched",
        "concept": "Fn03.C01",
        "related": ["Fn03.C02", "Fn03.C03"],
        "kind": "Ex",
        "bits": "0000-1000",
        "capability": "ACTIVITY_PAUSE_DISPATCH",
        "intent": "Advance one resumed Activity through the stock AOSP pause transaction.",
        "scope": "One authenticated inactive/background transition from RESUMED to PAUSED.",
        "trigger": "An inactive or background-source transition for a live RESUMED Activity.",
        "reads": "current lifecycle state, transition ledger and opaque token capability",
        "writes": "lifecycle state RESUMED→PAUSED and a pause terminal receipt",
        "positive": "PauseActivityItem invokes the real Activity.onPause exactly once on the Android main thread; for background-source A03 verdict ends at PAUSE_TERMINAL with the same transition left OPEN and does not require A04 STOP_TERMINAL.",
        "negative": "A non-RESUMED, stale, replayed or foreign transition is rejected without invoking onPause; a WMS/focus observation cannot act as a second trigger owner.",
        "failure": "Callback exception or delivery failure is visible as typed failure and cannot be converted into a PAUSED success.",
        "deps": [{"action_id": "Fn03.A02", "reason": "The verifier needs an independently prepared RESUMED pre-state."}],
    },
    "A04": {
        "title": "Activity onStop is dispatched",
        "concept": "Fn03.C01",
        "related": ["Fn03.C02", "Fn03.C03"],
        "kind": "Ex",
        "bits": "0000-1000",
        "capability": "ACTIVITY_STOP_DISPATCH",
        "intent": "Advance one paused Activity through the stock AOSP stop transaction.",
        "scope": "One authenticated background/hidden transition from PAUSED to STOPPED.",
        "trigger": "A reducer-validated background transition with source PAUSED; PAUSE_TERMINAL may be the same transition pause leg or a same-generation ledger fact from a prior inactive transition.",
        "reads": "current lifecycle state, transition ledger and opaque token capability",
        "writes": "lifecycle state PAUSED→STOPPED and a stop terminal receipt",
        "positive": "StopActivityItem invokes the real Activity.onStop exactly once on the Android main thread; STOP_TERMINAL closes either the same pause+stop transition or the direct PAUSED→BACKGROUND_NEW transition.",
        "negative": "A non-PAUSED, stale, duplicate or wrong-owner transition is rejected without callback or mutation; a WMS/focus observation cannot act as a second trigger owner.",
        "failure": "Delivery or callback failure remains a typed failure and never publishes STOPPED success.",
        "deps": [{"action_id": "Fn03.A03", "reason": "The verifier needs an independently prepared PAUSED pre-state."}],
    },
    "A05": {
        "title": "Activity finish routes to OH termination path",
        "concept": "Fn03.C01",
        "related": ["Fn03.C02", "Fn03.C03"],
        "kind": "Dl",
        "bits": "0001-0000",
        "capability": "ACTIVITY_FINISH_TERMINATE",
        "intent": "Translate an Android finish request into one OH termination request and revoke the instance only after terminal closure.",
        "scope": "Fn03 v1 covers Android-initiated finish from a CREATED Activity through destroy, OH termination and token invalidation; later source states require a future mapping revision.",
        "trigger": "An Android-initiated finish request for a live CREATED Activity; RESUMED/PAUSED/STOPPED and OH-initiated termination are outside v1.",
        "reads": "lifecycle state, finish ledger and opaque token capability",
        "writes": "ActivityLedger FINISH_REQUESTED→TERMINATING→DESTROYED→CLEANED, a three-fact TerminalJoin and post-join registry tombstone",
        "positive": "finishActivity sends one terminate request; after HOST_TERMINATE_ACCEPTED, an OH INITIAL leg matching ActivityBridgeKey+generation+FINISH_REQUESTED dispatches exactly one DestroyActivityItem; destroy and clean/death join to CLEANED.",
        "negative": "Unknown/foreign/stale token, non-CREATED v1 source, a different second finish_id while one is in flight, or destroyed instance is typed reject; same finish_id replay follows P02 idempotency.",
        "failure": "Native/OH rejection or a partial three-fact join leaves typed non-success or RECONCILE_REQUIRED; ActivityLedger never enters CLEANED and the old token remains guarded until all facts join.",
        "deps": [
            {"action_id": "Fn03.A01", "reason": "The verifier independently establishes the sole v1 CREATED pre-state."},
            {"action_id": "Fn03.A08", "reason": "Finish must resolve and later revoke the exact instance capability."},
        ],
        "preconditions_override": [
            "Fn03 Concept Bridge Contract is accepted with R1 as the primary route.",
            "FinishRequest carries authenticated owner, process_epoch, generation, token_handle, mapping_version and caller-provided finish_id; reducer validates then mints transition_id.",
            "The accepted lifecycle mapping_version is fn03-lifecycle-mapping-v1.",
        ],
    },
    "A06": {
        "title": "Android Activity states map to OH Ability lifecycle states",
        "concept": "Fn03.C02",
        "related": ["Fn03.C01", "Fn03.C03"],
        "kind": "Ex",
        "bits": "0000-1000",
        "capability": "LIFECYCLE_STATE_TRANSLATION",
        "intent": "Apply one versioned explicit mapping for the Fn03 v1 supported lifecycle edges and typed rejection for every other edge.",
        "scope": "Pure mapping and legality decision; it does not execute callbacks or send AbilityTransitionDone.",
        "trigger": "A typed OH lifecycle state with current Android state and mapping schema version.",
        "reads": "mapping schema version, source state, target state and current Activity state",
        "writes": "an immutable mapping decision containing transaction kind, required receipts or typed rejection",
        "positive": "Every supported state pair yields the documented Android transaction and required receipt set deterministically.",
        "negative": "For every explicit rejection, lifecycle-mapping-v1.yaml explicit_rejections[].reason is the exact expected reason; all other unknown/illegal edges use the schema unknown_policy and never dispatch callback.",
        "failure": "Schema mismatch or corrupt mapping refuses service; it never guesses a default lifecycle state.",
        "deps": [{"external_gate": "FN03_ACCEPTED_BRIDGE_CONTRACT", "reason": "The mapping schema is derived from the accepted cross-platform state contract."}],
    },
    "A07": {
        "title": "OH AbilityTransitionDone heartbeat is sent at the correct Android lifecycle point",
        "concept": "Fn03.C02",
        "related": ["Fn03.C01", "Fn03.C03", "Fn04.C05"],
        "kind": "Ex",
        "bits": "0000-1000",
        "capability": "TRANSITION_COMPLETION_SIGNAL",
        "intent": "Reduce required, matching terminal receipts into exactly one OH AbilityTransitionDone acknowledgement.",
        "scope": "One transition-specific completion reducer: success may emit OH AbilityTransitionDone; failure emits only a Bridge-local typed record and no synthetic OH failure message.",
        "trigger": "Arrival of a terminal lifecycle or foreground-ready receipt for an open OH transition.",
        "reads": "mapping decision, transition ledger, opaque capability and required receipt set",
        "writes": "ACKED or FAILED terminal transition state and one OH completion call record",
        "positive": "All required receipts match token, generation and transition; exactly one AbilityTransitionDone is sent and only the matching typed OH server acceptance moves the transition to ACKED.",
        "negative": "Missing, duplicate, out-of-order, foreign or stale receipts do not send a success ACK.",
        "failure": "A definite nonzero OH result enters Bridge-local FAILED_TYPED; unknown delivery enters RECONCILE_REQUIRED and cannot resend before reconciliation; A10 DISPLAY_FAILED enters FAILED_TYPED/FIRST_FRAME_NOT_PRESENTED; no failure path calls AbilityTransitionDone or invents an OH failure message.",
        "deps": [
            {"action_id": "Fn03.A06", "reason": "The reducer consumes the versioned mapping decision."},
            {"action_id": "Fn03.A08", "reason": "The OH call must resolve the live native token capability."},
            {"action_id": "Fn03.A10", "reason": "Conditional dependency: only requireFirstFrame=true foreground transitions consume A10 foreground-ready; other transitions do not."},
        ],
    },
    "A08": {
        "title": "Android Activity token is bridged to OH token and back where required",
        "concept": "Fn03.C03",
        "related": ["Fn03.C01", "Fn03.C02"],
        "kind": "Cc",
        "bits": "0000-0010",
        "capability": "ACTIVITY_TOKEN_CORRELATION",
        "intent": "Maintain one native, owner- and generation-bound opaque capability for each live Android/OH Activity pair.",
        "scope": "Atomic register, resolve both directions and revoke operations for one live instance.",
        "trigger": "Register, resolve or revoke request at the native adapter boundary.",
        "reads": "native registry, caller owner, process_epoch, generation and capability nonce",
        "writes": "atomic bidirectional registry entry, tombstone and auditable operation receipt",
        "positive": "A registered pair resolves both directions only for the exact owner and generation; exact duplicate register is idempotent and returns the original capability; revocation makes both directions fail immediately.",
        "negative": "Forged handle, raw address, wrong owner, old generation and revoked capability fail closed; reused nonce with a different token-pair payload is NONCE_PAYLOAD_CONFLICT.",
        "failure": "Partial insertion or removal rolls back both indexes; native death/restart invalidates old capabilities and cannot leave a one-sided mapping.",
        "deps": [
            {"external_gate": "AUTHENTICATED_OH_TOKEN_FIXTURE", "reason": "Independent tests require a typed OH token fixture without relying on another Fn03 Action."},
            {"external_gate": "FN03_A09_REGISTER_REQUEST_FIXTURE", "reason": "A09 launch ingress is the product caller of REGISTER; verifier injects the request without inheriting A09 verdict."},
        ],
        "preconditions_override": [
            "Fn03 Concept Bridge Contract is accepted with R1 as the primary route.",
            "Registry input carries authenticated owner, process_epoch, generation, op and nonce; transition_id is explicitly not used.",
        ],
    },
    "A09": {
        "title": "OH AppScheduler launch callbacks enter Android ApplicationThread semantics",
        "concept": "Fn03.C01",
        "related": ["Fn03.C03", "Fn02.C01", "Fn06"],
        "kind": "Cr",
        "bits": "1000-0000",
        "capability": "APPLICATIONTHREAD_LAUNCH_INGRESS",
        "intent": "Translate OH AppScheduler bind and launch callbacks into typed Android ApplicationThread inputs.",
        "scope": "Application bind admission and one Activity launch ingress, ending when a validated LaunchEnvelope enters the unique reducer queue and receives an ingress receipt; A01 owns ClientTransaction delivery and onCreate.",
        "trigger": "OH ScheduleLaunchApplication or ScheduleLaunchAbility callback with authenticated launch data.",
        "reads": "process bind state, package/component data, configuration and native token capability",
        "writes": "bind-once state, QUEUED_AWAITING_BIND pending entry, admitted LaunchEnvelope in the unique reducer queue and ingress receipt",
        "positive": "bindApplication occurs at most once per process epoch; same-epoch BOUND releases each matching QUEUED_AWAITING_BIND entry exactly once into the reducer queue, preserving identity and not claiming A01 delivery or onCreate.",
        "negative": "UNBOUND/BINDING launch is held only in typed QUEUED_AWAITING_BIND and is not admitted; wrong package/owner, stale epoch or malformed fields are always typed reject and never queued; epoch/generation change invalidates pending entries.",
        "failure": "JNI/binder failure returns typed ingress failure; BIND_FAILED makes every same-epoch QUEUED_AWAITING_BIND entry FAILED_TYPED and never admitted; timeout fails, and new epoch invalidates pending.",
        "deps": [
            {"action_id": "Fn02.A05", "reason": "The application bind payload must be prepared before launch ingress."},
            {"action_id": "Fn03.A08", "reason": "The launch envelope carries a live opaque instance capability."},
        ],
        "preconditions_override": [
            "Bind leg carries package/process/user/process_epoch and bind_id; activity_generation and token_handle are explicitly ABSENT.",
            "Launch leg carries full ActivityBridgeKey, launch_id, token capabilities, intent, activityInfo and config; pre-BOUND is pending, BOUND controls admission; A01 later mints lifecycle transition_id.",
        ],
    },
    "A10": {
        "title": "Lifecycle foreground completion can be gated by first-frame readiness",
        "concept": "Fn03.C02",
        "related": ["Fn03.C01", "Fn03.C03", "Fn04.C05"],
        "kind": "Ex",
        "bits": "0000-1000",
        "capability": "FIRST_FRAME_LIFECYCLE_GATE",
        "intent": "Join a real resume receipt with a typed first-content-present receipt before declaring foreground ready.",
        "scope": "One pending foreground transition and its two implementation-independent receipt inputs.",
        "trigger": "A10 consumes an accepted require_first_frame=true mapping decision, creates the join and enters AWAITING_FIRST_FRAME; later receipts advance it.",
        "reads": "pending transition, DisplayLedger, token, window, generation, frame and content-origin identities",
        "writes": "At most one open join per ActivityBridgeKey+windowGeneration; DisplayLedger NOT_REQUIRED→AWAITING_FIRST_FRAME→PRESENTED or DISPLAY_FAILED, join state and one foreground-ready receipt",
        "positive": "Only the current unique open join accepts matching resume and APP_CONTENT present receipts and produces exactly one foreground-ready; superseded joins can never reopen.",
        "negative": "require_first_frame=false creates no join; present before any open join is NO_OPEN_FIRST_FRAME_JOIN and not buffered; later lifecycle supersedes old join; wrong identity/placeholder/duplicate/stale never readies.",
        "failure": "Missing input remains visibly pending or fails by policy; timeout, screenshot, surface existence and onDraw alone never synthesize success.",
        "deps": [
            {"action_id": "Fn03.A02", "reason": "The gate consumes an independent real resume receipt."},
            {"action_id": "Fn03.A06", "reason": "Join creation consumes A06's versioned mapping decision with require_first_frame=true."},
            {"external_gate": "Fn04.A02_TYPED_FIRST_CONTENT_PRESENT_RECEIPT", "reason": "Fn04.C05 owns production and device proof of the first-content-present fact."},
        ],
        "preconditions": [
            "Only an open foreground transition whose mapping decision sets require_first_frame=true may create this join.",
        ],
    },
}


def atom_yaml(action_id: str, item: dict) -> dict:
    evidence_output = (
        "绑定 action_id/token_handle/owner/process_epoch/generation/transition_id 的输入、"
        "状态前后、typed receipt、原始 stdout/stderr、构建与设备身份。"
    )
    if action_id == "Fn03.A05":
        evidence_output += (
            " A05 额外保存 caller finish_id 与 reducer-minted transition_id 的同代关联。"
        )
    elif action_id == "Fn03.A09":
        evidence_output = (
            "Bind 腿以 package/process/user/process_epoch/bind_id 关联，token_handle、"
            "activity_generation、launch_id 显式 ABSENT；launch 腿以完整 "
            "ActivityBridgeKey/launch_id/token capabilities 关联，并保存 immutable payload hash。"
        )
    elif action_id == "Fn03.A08":
        evidence_output = (
            "Registry 操作以 action_id/op/owner/process_epoch/generation/nonce 关联；保存 "
            "TokenRegistryRequest/Receipt、双索引前后、handle/tombstone 与原始证据。"
        )
    mapping_negative = (
        ""
        if action_id in {"Fn03.A08", "Fn03.A09"}
        else " Wrong mapping_version is rejected before any callback."
    )
    return {
        "schema_version": "1.0",
        "action_id": action_id,
        "kind": "FUNCTION_ACTION",
        "title": item["title"],
        "concept_id": item["concept"],
        "related_concepts": item["related"],
        "action_kind": item["kind"],
        "capability_name": item["capability"],
        "capability_bits": item["bits"],
        "contract_status": "READY",
        "domain": {
            "id": "Fn03",
            "name": "Activity 生命周期",
            "boundary": f"只覆盖 {item['scope']}，并以独立 P/N/F verdict 为边界。",
        },
        "legacy_ids": [f"L04.{action_id[-3:]}"],
        "lifecycle_status": "DESIGN_READY_NOT_IMPLEMENTED",
        "definition": {
            "intent": item["intent"],
            "scope": item["scope"],
            "non_goals": [
                "不修改 AOSP ActivityThread/ClientTransaction 或 OpenHarmony AbilityManager 的内部语义。",
                "不把桥调用返回、日志、进程存活、窗口壳或相邻 Action 的 PASS 当作本 Action 成功。",
                "不启用 R2 lifecycle broker；未来升级必须重新取证、评审并由 owner 裁决。",
            ],
            "observer": "未参与实现的 verifier，通过公开边界、typed receipt、状态 readback 与原始日志观察。",
            "trigger": item["trigger"],
            "preconditions": item.get(
                "preconditions_override",
                COMMON_PRECONDITIONS + item.get("preconditions", []),
            ),
            "state_reads": [item["reads"]],
            "state_writes": [item["writes"]],
            "positive_oracle": item["positive"],
            "negative_oracle": item["negative"] + mapping_negative,
            "failure_oracle": item["failure"],
            "evidence_output": evidence_output,
        },
        "depends_on": item["deps"],
        "source_refs": [
            "docs/concepts/Fn03/BRIDGE_CONTRACT.md",
            "docs/concepts/Fn03/STRATEGY_DECISION.md",
            f"docs/atoms/Fn03/{action_id[-3:]}/history.md",
        ],
        "maturity": {"CM": "UNRATED", "VM": "UNRATED", "DM": "UNRATED"},
    }


def verification_text(action_id: str, item: dict) -> str:
    dependency_lines = "\n".join(
        f"- 依赖 `{dependency.get('action_id') or dependency.get('external_gate')}`：{dependency['reason']}"
        for dependency in item["deps"]
    )
    owner_case = ""
    if action_id == "Fn03.A03":
        owner_case = """
### N03 单一 trigger owner

在同一 transition 前后注入 WMS/focus 观测事件；它只能进入观测账本，不得生成第二个
PauseActivityItem、onPause callback 或 PAUSE_TERMINAL。唯一 trigger owner 是 OH Ability lifecycle。
"""
    elif action_id == "Fn03.A04":
        owner_case = """
### N03 单一 trigger owner

在同一 transition 前后注入 WMS/focus 观测事件；它只能进入观测账本，不得生成第二个
StopActivityItem、onStop callback 或 STOP_TERMINAL。唯一 trigger owner 是 OH Ability lifecycle。
"""
    evidence_addendum = ""
    if action_id == "Fn03.A05":
        evidence_addendum = (
            "A05 还必须分别保存 host terminate accepted、Android destroyed、OH clean/death"
            " 三份同代 receipt、OH INITIAL leg transition_id 与 TerminalJoin 前后状态。"
        )
    elif action_id == "Fn03.A06":
        evidence_addendum = "A06 还必须保存 mapping schema version 与 schema artifact SHA-256。"
    elif action_id == "Fn03.A07":
        evidence_addendum = (
            "A07 还必须保存 OH server hostResult；非零结果只能进入 FAILED，不能进入 ACKED。"
        )
    elif action_id == "Fn03.A08":
        evidence_addendum = (
            "A08 还必须保存 exact duplicate register 返回同一 capability 的幂等证据。"
        )
    elif action_id == "Fn03.A09":
        evidence_addendum = (
            "A09 还必须保存 bind-once counter、同代 bind terminal receipt 与"
            " ProcessBindLedger UNBOUND→BINDING→BOUND readback。"
        )
    elif action_id == "Fn03.A10":
        evidence_addendum = (
            "A10 必须保存 Fn04.C05 typed producer identity、windowGeneration、frameId、"
            "presentOutcome、content-origin 以及关联 Fn04 evidence run 的 SHA-256。"
        )
    registry_replay = ""
    if action_id == "Fn03.A08":
        registry_replay = (
            "对 register，完全相同 identity 的重复注册必须幂等返回原 capability；"
            "不同 owner/generation 必须形成隔离 identity 或 typed reject。"
        )
    elif action_id == "Fn03.A05":
        registry_replay = (
            "TerminalJoin 未闭合时，同 finish_id 重放必须返回同一 reducer-minted "
            "transition_id，零新增 terminate request、零 mutation；闭合后重复 finish "
            "命中 tombstone 并幂等拒绝，旧 token 不可解析。"
        )
    failure_addendum = ""
    if action_id == "Fn03.A05":
        failure_addendum = """
### F03 Partial TerminalJoin

host terminate accepted、Android destroyed、OH clean/death 任一事实缺失，且达到 policy
`terminal_join_timeout`（monotonic，首个同代 terminal fact 后 5000ms）或结果 unknown
时，必须以 `TERMINAL_JOIN_TIMEOUT` 进入 RECONCILE_REQUIRED；
ActivityLedger 不得进入 CLEANED，旧 token 的防重/tombstone guard 不得失效。
若 HOST_TERMINATE_ACCEPTED 已存在而 OH INITIAL 腿始终缺失，整个等待与 timeout
期间 DestroyActivityItem 投递数和 destroy receipt 数必须保持 0。

### F04 destroy callback_timeout

finish 接受后 destroy 腿进入 TransitionLedger QUEUED 即启动 monotonic 5000ms
`callback_timeout`；全静默时以 `CALLBACK_TIMEOUT` 进入 RECONCILE_REQUIRED，
不得进入 CLEANED，capability tombstone 和防重 guard 不得失效。

### F05 host_terminate_accept_timeout

OH terminate request 发出即启动 monotonic 5000ms；host 既不接受也不拒绝，或
INITIAL 已在 QUEUED_AWAITING_HOST_ACCEPT 但接受永不到达时，以
`HOST_TERMINATE_ACCEPT_TIMEOUT` 进入 RECONCILE_REQUIRED，不投递 destroy，并保留
tombstone 与防重 guard。
"""
    replay_negative = "N01/N02/N03" if owner_case else "N01/N02"
    supplementary = ""
    if action_id == "Fn03.A02":
        supplementary = """
### P03 补充 resume 分支

使用 PAUSED_STOPPED_REFERENCE_FIXTURE：PAUSED 必须 onResume；STOPPED 必须依次
onRestart→onStart→onResume。P03 是 A02 最终 PASS 的阻塞用例，但 fixture 直接按
Contract 建立，不使用 A03/A04 实现或继承其 verdict。
"""
    elif action_id == "Fn03.A04":
        supplementary = """
### P03 独立 PAUSED→BACKGROUND_NEW

用同代 ledger fixture 提供已由先前 inactive transition 闭合的 PAUSE_TERMINAL，
再以新的 transition_id 提交 background；真实 onStop 和 STOP_TERMINAL 必须闭合这个
新 transition。fixture 只建前态，不继承 A03 verdict。

### P04 同 transition 的 stop leg

对 `ONE_TRANSITION_ID_TWO_ACTION_RECEIPTS`，A03 的 PAUSE_TERMINAL 与 A04 的
STOP_TERMINAL 共享 transition_id，但以 action_id 区分；A04 不得把合法第二腿当作
duplicate，STOP_TERMINAL 必须闭合该 background transition。
"""
    elif action_id == "Fn03.A05":
        supplementary = """
### P05 INITIAL 早到后单次放行

先提交同代 OH INITIAL，使其进入 QUEUED_AWAITING_HOST_ACCEPT；排队期间
DestroyActivityItem 投递数必须为 0。随后注入 HOST_TERMINATE_ACCEPTED，投递数和
ANDROID_DESTROYED receipt 均必须恰好为 1，TerminalJoin 继续按 P01 闭合。
"""
    timeout_case = ""
    if action_id in {"Fn03.A01", "Fn03.A02", "Fn03.A03", "Fn03.A04"}:
        forbidden = {
            "Fn03.A01": "CREATED",
            "Fn03.A02": "RESUMED",
            "Fn03.A03": "PAUSED",
            "Fn03.A04": "STOPPED",
        }[action_id]
        timeout_case = f"""
### F03 callback_timeout

按 `fn03-timeout-policy-v1`：每个 `(action_id,transition_id)` dispatch leg 进入
QUEUED 后独立 arm monotonic 5000ms；
未收到真实 callback 时以 `CALLBACK_TIMEOUT` 进入 RECONCILE_REQUIRED，不得发布
`{forbidden}` receipt，不得合成 callback、ACK 或后续状态。测试使用注入时钟，不做
真实 5 秒 sleep。
"""
        if action_id in {"Fn03.A03", "Fn03.A04"}:
            timeout_owner = (
                "A03 只作为共享 transition 策略观察方；其 PAUSE_TERMINAL Action verdict "
                "保持成功且不被 transition reconcile 翻转；失败归 A07/TransitionLedger 域。"
                if action_id == "Fn03.A03"
                else "A04 通过 TransitionLedger readback 核验未 dispatch 的 stop leg；"
                "共享 reconcile 归 A07/TransitionLedger 域，不翻转 A04 P01/P03/P04。"
            )
            timeout_case += f"""
### F04 background leg gap

A03 PAUSE_TERMINAL 后同 background transition 保持 OPEN，并独立启动 5000ms
`background_leg_gap_timeout`；A04 stop leg 未在期限内进入 QUEUED 时，以
`BACKGROUND_STOP_LEG_NOT_QUEUED` 进入 RECONCILE_REQUIRED，不合成 STOPPED。
{timeout_owner}
"""
    elif action_id == "Fn03.A09":
        timeout_case = """
### F03 bind_wait_timeout

QUEUED_AWAITING_BIND 接受后 monotonic 5000ms 未收到同代 BOUND receipt，以
`BIND_WAIT_TIMEOUT` 进入 FAILED_TYPED；该 LaunchEnvelope 此后永不 admission。

### F04 bind terminal failure

同 epoch bind terminal receipt 为 BIND_FAILED 时，所有 QUEUED_AWAITING_BIND entries
立即以 typed bind reason 进入 FAILED_TYPED，之后收到 BOUND 或重放也不得 admission。
"""
    elif action_id == "Fn03.A10":
        timeout_case = """
### F03 first_frame_timeout

DisplayLedger 进入 AWAITING_FIRST_FRAME 后 monotonic 5000ms 无合格 Fn04 receipt，
以 `FIRST_FRAME_TIMEOUT` 进入 DISPLAY_FAILED，不得合成 present 或 foreground-ready。
"""
    elif action_id == "Fn03.A07":
        timeout_case = """
### F03 first-frame failure propagation

require_first_frame=true 时，A10 的 DISPLAY_FAILED/FAILED 是 A07 的 terminal 失败输入；
A07 必须以 `FIRST_FRAME_NOT_PRESENTED` 进入 FAILED_TYPED，不发送
AbilityTransitionDone，不得无限等待或改记成功。

### F04 host_ack_timeout

AbilityTransitionDone 发送后 monotonic 5000ms 未收到 hostResult，以
`HOST_ACK_TIMEOUT` 进入 RECONCILE_REQUIRED；reconcile 证明服务端未接受前禁止重发，
任何时候都不得产生第二次服务端 acceptance。
"""
    if action_id == "Fn03.A05":
        identity_line = (
            "- A05 输入显式固定 owner、process_epoch、generation、token_handle、"
            "mapping_version 与 finish_id；transition_id 由 reducer 铸造并通过 receipt 观察。"
        )
        stimulus_identity = (
            "verifier 保存 finish_id；首次提交后保存 reducer 铸造的 transition_id，重放沿用"
            "原 finish_id 并必须关联回同一 transition_id。"
        )
        evidence_identity = "A05 必须保存 finish_id↔transition_id 的同代 reducer mint 关联记录。"
    elif action_id == "Fn03.A09":
        identity_line = (
            "- Bind 固定 package/process/user/process_epoch/bind_id，token_handle/"
            "activity_generation/launch_id 显式 ABSENT；launch 固定完整 ActivityBridgeKey 与 launch_id。"
        )
        stimulus_identity = (
            "bind 重放保留 bind_id；launch 正负失败用例使用 launch_id。两条腿的证据 join "
            "键不得混用。"
        )
        evidence_identity = (
            "A09 bind 腿以 bindId 关联 ProcessBindLedger；launch 腿使用 ActivityBridgeKey/"
            "launchId/payloadDigest，A01 后续 mint transition_id 不属于 A09 verdict。"
        )
    elif action_id == "Fn03.A08":
        identity_line = (
            "- Registry 请求固定 op、owner、process_epoch、generation 与 nonce；"
            "resolve/revoke 另携 capability_handle，不使用 transition_id。"
        )
        stimulus_identity = (
            "每个新 registry operation 使用新 nonce；exact register replay 保留原 nonce，"
            "双向 resolve/revoke 保存 handle 与 tombstone。"
        )
        evidence_identity = (
            "A08 以 op/owner/process_epoch/generation/nonce join request、receipt 和双索引状态。"
        )
    else:
        identity_line = "- 测试输入显式固定 owner、process_epoch、generation、transition_id 与 action_id。"
        stimulus_identity = "正向、负向、失败注入分别使用新的 transition_id，重放用例保留原 ID。"
        evidence_identity = ""
    positive_replay = (
        "P01/P02/P03/P04"
        if action_id == "Fn03.A04"
        else "P01/P02/P03"
        if action_id == "Fn03.A02"
        else "P01/P02/P05"
        if action_id == "Fn03.A05"
        else "P01/P02"
    )
    mapping_negative = (
        ""
        if action_id in {"Fn03.A08", "Fn03.A09"}
        else " Wrong mapping_version 必须在任何 callback 或状态 mutation 前拒绝。"
    )
    mapping_precondition = (
        ""
        if action_id in {"Fn03.A08", "Fn03.A09"}
        else "- 合法 mapping_version 固定为 `fn03-lifecycle-mapping-v1`；其它值走 N01。"
    )
    replay_core = {
        "Fn03.A06": "同一 mapping request 重放必须返回同一 immutable decision，不新增状态或执行 callback/ACK。",
        "Fn03.A07": "同一 terminal receipt 重放不得发送第二次 AbilityTransitionDone 或形成第二次 host acceptance。",
        "Fn03.A08": "同一 registry operation nonce 重放服从下述 register/resolve/revoke 幂等合同。",
        "Fn03.A09": "同 bind_id/launch_id 重放返回原 ingress receipt，不产生第二次 bind 或 launch admission。",
        "Fn03.A10": "同一 resume/present receipt 重放不得产生第二个 foreground-ready 或重开 superseded join。",
    }.get(
        action_id,
        "同一 terminal transition 重放不得执行第二次本 Action callback 或创建第二份权威状态。",
    )
    return f"""---
schema_version: '1.0'
action_id: {action_id}
status: FROZEN_IMPLEMENTATION_INDEPENDENT
selected_route: R1
future_upgrade_route: R2
final_verifier_requirement: independent_agent_not_implementer
---

# {action_id} 独立 Verification Specification

## Observable behavior

{item["intent"]} 独立验收只观察公开输入、typed receipt、状态 readback 和原始
evidence；不得读取私有实现变量，也不得以 build 成功、JNI 返回、日志、进程存活、
窗口壳、截图或相邻 Action verdict 替代本 Action 的行为结果。

## Preconditions and dependencies

- Fn03 Concept 已接受 R1 为主方案，R2 只是未来升级方向。
{identity_line}
{mapping_precondition}
- 依赖只建立可复现前态，不把依赖 Action 的汇总 verdict 继承为本 Action PASS。
{dependency_lines}

## Stimulus

{item["trigger"]} verifier 保存请求和前态 SHA-256，然后经真实公开边界提交一次；
{stimulus_identity}

## Positive cases and oracle

### P01 核心成功

{item["positive"]}

{supplementary}

### P02 重放与边界

{replay_core} 更换合法 token/generation/component 后仍满足同一合同，不得硬编码测试包。
{registry_replay}

## Negative cases and oracle

### N01 身份与状态错配

{item["negative"]}{mapping_negative}

### N02 负向无副作用

保存调用前后 registry、lifecycle ledger、callback count 与 OH call count；typed reject
后这些权威状态必须保持不变，且 denied、stale、duplicate、illegal 和 unsupported
不能压成一个 Boolean。

{owner_case}

## Failure cases and oracle

### F01 边界故障

{item["failure"]}

{failure_addendum}
{timeout_case}

### F02 Restart/replay

在最早 durable/observable seam 后模拟 native death 或进程 epoch 变化；旧 capability
与旧 transition 不得在新 epoch 复活，恢复后也不得出现 ghost state 或 success receipt。

## Raw evidence outputs

每次 run 保存到 `var/evidence/atoms/Fn03/{action_id[-3:]}/runs/<run-id>/`，至少包含
manifest、commands、stdout/stderr、request/response、before/after state、
source/artifact SHA-256、host/device identity、callback/ACK counters 和 verifier verdict。
{evidence_addendum}
{evidence_identity}

## Independent replay procedure

1. 校验 atom、design、verification 与 implementation handoff hash；
2. 独立建立前态，不复用实现者声称的 PASS；
3. 依次执行 {positive_replay}、{replay_negative}、F01/F02/F03/F04/F05（若定义）并保存原始输出；
4. 行为不符给 FAIL，外部能力或设备不可用给 BLOCK，合同歧义给 SPEC_GAP；
5. 全部满足才给 PASS，并记录 verifier identity 与独立性声明。

## Implementation independence

规约绑定输入、外部状态、输出和证据，不绑定具体类、容器或锁。R1 必须保持
adapter reducer + native opaque capability + stock AOSP transaction；R2 不会自动
切换。最终验收者不得是实现者。
"""


def design_text(action_id: str, item: dict) -> str:
    mapping_section = ""
    if action_id == "Fn03.A06":
        transition_rows = "\n".join(
            "| `{source}` | `{target}` | `{transactions}` | `{callbacks}` | `{receipts}` | `{frame}` |".format(
                source=row["source"],
                target=row["oh_target"],
                transactions=" + ".join(row["android_transactions"]),
                callbacks=" + ".join(row["required_callbacks"]),
                receipts=" + ".join(row["required_receipts"]),
                frame=row["require_first_frame_effect"],
            )
            for row in MAPPING_SCHEMA["transitions"]
        )
        mapping_section = f"""
## Frozen lifecycle mapping schema

权威工件是 `docs/spec/concepts/Fn03/lifecycle-mapping-v1.yaml`，SHA-256 为
`{MAPPING_SCHEMA_SHA256}`。unknown source/target 或未列 edge 一律在 callback 前
`REJECT_UNSUPPORTED_STATE_BEFORE_CALLBACK`，不得把数值 enum 直接 cast。

| Bridge source | OH target | Android transaction | Required callbacks | Required receipts | require_first_frame |
|---|---|---|---|---|---|
{transition_rows}

`RESUMED→BACKGROUND_NEW` 只使用一个 transition_id 和两个 Action receipt：
A03 在 `PAUSE_TERMINAL` 后独立给出 pause verdict 并保持 ledger OPEN，不等待 A04；
A04 消费相同 transition context，在 `STOP_TERMINAL` 后负责闭合。
v1 不声称覆盖所有平台 edge：`STOPPED→INITIAL` OH-initiated termination 以
`UNSUPPORTED_OH_INITIATED_TERMINATION_V1` 在 callback 前拒绝；扩展它必须先修订
Contract/Action，而不能由实现者自行加表项。
`FINISH_REQUESTED→INITIAL` 的 dispatch_owner 固定为 OH INITIAL leg；finish ingress
不投递 destroy，早到 INITIAL 等待 HOST_TERMINATE_ACCEPTED 后才单次放行。
"""
    elif action_id == "Fn03.A10":
        mapping_section = """
## Fn04 typed receipt interface

A10 只消费 Fn04.C05（当前 producer Action 为 Fn04.A02）定义的
`FirstFrameReceipt{key, window_generation, frame_id, present_outcome,
content_origin, producer_action_id, evidence_run_sha256}`。`content_origin` 必须是
typed `APP_CONTENT` 才能通过；`STARTING_WINDOW`、`PLACEHOLDER`、`UNKNOWN` 均拒绝。
Fn03 不根据截图、surface、swap 或 OnDraw 自行推导该字段。
早到 present 在没有 open join 时 fail-closed，不缓存；这是明确的 liveness 取舍，
必须由 D200 时序证据复核，不能用 timeout 假成功补偿。
"""
    elif action_id == "Fn03.A08":
        mapping_section = """
## Tombstone retention

A08 不自行决定 tombstone 的提前删除。TerminalJoin 同代闭合前必须保留；闭合后按
Contract 的有界保留策略清理。nonce replay 与 revoked handle 在保留期内始终得到
同一 typed terminal reason。
"""
    interface_definition = """输入为带 schema version 的 `LifecycleEnvelope`：
`{action_id, owner, process_epoch, generation, token_handle, transition_id, source_state,
target_state, mapping_version, require_first_frame, monotonic_time}`。"""
    if action_id == "Fn03.A05":
        interface_definition = """Android `Activity.finish()` 经
`IActivityClientController.finishActivity` adapter 形成
`FinishRequest{action_id, owner, process_epoch, generation, token_handle, mapping_version,
finish_id}`；reducer 在任何状态 mutation 前校验 mapping_version，再生成 transition_id
并只请求 OH terminate，不投递 DestroyActivityItem。
随后 OH `INITIAL` LifecycleEnvelope 以同一 ActivityBridgeKey、generation 和
ActivityLedger=FINISH_REQUESTED 关联；它可以带独立 OH transition_id，且只有这一入口
投递一次 stock AOSP DestroyActivityItem。若 INITIAL 早于 HOST_TERMINATE_ACCEPTED，
只进入 `QUEUED_AWAITING_HOST_ACCEPT`，接受后单次放行；拒绝或
`host_terminate_accept_timeout` 则不投递。"""
    elif action_id == "Fn03.A09":
        interface_definition = """A09 有两条不混用身份的入口：
`BindEnvelope{package,process,user,process_epoch,bind_id,payload_digest}`，其中
activity_generation/token_handle/launch_id 显式 ABSENT；以及完整
`LaunchEnvelope{ActivityBridgeKey,launch_id,oh_token_capability,
android_token_capability,intent,activityInfo,config,payload_digest}`。
LaunchEnvelope 在 UNBOUND/BINDING 时接受为 typed `QUEUED_AWAITING_BIND` pending，
只有同 epoch BOUND terminal receipt 才允许 admission 入 reducer queue。
bind evidence 以 `(package,process,user,process_epoch,bind_id)` join；launch evidence
以 `(ActivityBridgeKey,launch_id,payload_digest)` join。payload_digest 覆盖 envelope
内 immutable intent/activityInfo/config bytes，由 A09 pending/queue owner 持有直到
A01 dequeue；A01 才从 launch_id mint lifecycle transition_id。"""
    elif action_id == "Fn03.A08":
        interface_definition = """输入为
`TokenRegistryRequest{op:REGISTER|RESOLVE_FWD|RESOLVE_REV|REVOKE, owner,
process_epoch, generation, nonce, oh_token_capability?, android_token_capability?,
capability_handle?}`。REGISTER exact replay 返回原 handle；resolve 只返回授权 peer
capability；revoke 返回 tombstone_ref。"""
    output_definition = """输出为 `LifecycleReceipt`：
`{action_id, status, reason, observed_callback, mapped_state, owner, process_epoch,
token_handle, generation, transition_id}`。"""
    idempotency_clause = (
        "共享 reducer 以 `(action_id, owner, process_epoch, generation, token_handle, "
        "transition_id)` 为幂等键。"
    )
    if action_id in {"Fn03.A03", "Fn03.A04"}:
        idempotency_clause += (
            "同 transition_id 的 A03 pause leg 与 A04 stop leg 因 action_id 不同而可区分。"
        )
    evidence_join = (
        "action_id + owner + process_epoch + capability + generation + transition_id"
    )
    mapping_guard = "wrong mapping_version 必须在 callback 前 fail-closed；"
    mapping_pin = (
        f"mapping_version 固定为 `fn03-lifecycle-mapping-v1`，mapping artifact SHA-256 "
        f"`{MAPPING_SCHEMA_SHA256}`；"
    )
    if action_id == "Fn03.A08":
        output_definition = """输出只使用
`TokenRegistryReceipt{op,status,reason,owner,process_epoch,generation,nonce,
capability_handle?,peer_capability?,tombstone_ref?}`。"""
        idempotency_clause = (
            "registry 以 `(action_id, op, owner, process_epoch, generation, nonce)` "
            "作为 operation 幂等键；capability_handle 是 resolve/revoke 参数，不替代 nonce。"
        )
        evidence_join = "action_id + op + owner + process_epoch + generation + nonce"
        mapping_guard = ""
        mapping_pin = ""
    elif action_id == "Fn03.A09":
        output_definition = """bind 输出
`BindIngressReceipt{package,process,user,process_epoch,bind_id,status,reason}`；
launch 输出 `LaunchIngressReceipt{ActivityBridgeKey,launch_id,payload_digest,
status,reason,queue_sequence}`。"""
        idempotency_clause = (
            "bind 以 `(action_id, package, process, user, process_epoch, bind_id)` 幂等；"
            "launch 以 `(action_id, ActivityBridgeKey, launch_id, payload_digest)` 幂等；"
            "两者不得混用，transition_id 由 A01 后续 mint。"
        )
        evidence_join = "bind_id（bind 腿）或 ActivityBridgeKey + launch_id + payload_digest（launch 腿）"
        mapping_guard = ""
        mapping_pin = ""
    if action_id == "Fn03.A06":
        first_frame_state = (
            "require_first_frame_effect 由 frozen mapping 按 edge 决定：foreground "
            "edge 输出 ADD_FOREGROUND_READY_FROM_A10_WHEN_TRUE，其余 edge 输出 "
            "NOT_APPLICABLE；A06 只输出 mapping decision，不创建 A10 join。"
        )
    elif action_id == "Fn03.A07":
        first_frame_state = (
            "require_first_frame=true 时 A07 等待 A10 foreground-ready，false 时只消费 "
            "callback receipt；A07 自身不创建 first-frame join。"
        )
    elif action_id in {"Fn03.A02", "Fn03.A10"}:
        first_frame_state = (
            "require_first_frame=true 时 foreground completion 必须等待 A10；false 时不得创建 join。"
        )
    else:
        first_frame_state = (
            "本 Action 的 require_first_frame_effect 为 NOT_APPLICABLE，不得创建 A10 join。"
        )
    return f"""---
schema_version: '1.0'
action_id: {action_id}
status: FROZEN_FOR_IMPLEMENTATION
selected_route: R1
future_upgrade_route: R2
---

# {action_id} {item["capability"]} · DESIGN_SPEC

## 已选路线

裁决路线是 R1：边界 adapter 只做认证、映射、去重和 receipt 汇聚；实例身份由
native owner/generation-bound opaque capability 表示；Activity callback 继续走
未修改的 AOSP ClientTransaction/ActivityThread 主链。R2 独立 lifecycle broker
仅为未来升级，不是 fallback，不能由实现者自动启用。

## Module placement / 模块位置

共享、可 host-test 的 reducer 和 registry 位于
`src/vendor/upstream/sources/oh61-v7-b2133b5b/framework/activity/core/`；OH/JNI ingress 位于
同版本 `framework/activity/jni/`；Java 薄桥位于 `framework/activity/java/`。
Action 兼容目录 `src/atoms/Fn03/{action_id[-3:]}/` 只保存 IMPLEMENTATION handoff
和 Action 测试入口，不复制第二份产品逻辑。

## Interfaces / 接口

{interface_definition} {output_definition}
本 Action 的具体意图为：{item["intent"]}

{mapping_section}

## State / 状态

本 Action 读取 {item["reads"]}；只写 {item["writes"]}。{idempotency_clause}
{mapping_pin}{mapping_guard}{first_frame_state} 所有 terminal 结果
不可从 SUCCESS 回退；epoch 或 generation 改变使旧 capability
和未闭合 transition 失效。native registry 的正反索引必须在同一临界区原子更新。

## Failure semantics / 失败语义

{item["failure"]} 所有错误使用 typed reason；{mapping_guard}timeout 必须服从
`docs/spec/concepts/Fn03/timeout-policy-v1.yaml`
（SHA-256 `{TIMEOUT_POLICY_SHA256}`），只能产生等待或失败，不得
产生成功。Java/JNI/native/OH 任一边界返回错误时，外层必须保留原 action、token、
generation 和 transition 关联，禁止吞错、默认成功、裸地址身份和延时假 ACK。

## Change manifest / 变更清单

- 新增共享 lifecycle core：版本化 envelope、state mapper、token registry、
  transition reducer 与 first-frame join。
- 收窄现有 Java/JNI bridge：不再以 `jlong tokenAddr` 或 Java map 作为身份真源。
- 保留 stock AOSP transaction/callback 路径；不修改 APK、ART 或 AOSP Framework 语义。
- 在 `src/atoms/Fn03/{action_id[-3:]}/` 保存 hash-bound implementation handoff 与测试命令。

## Build integration / 构建集成

纯 C++ core 作为独立 host test target 编译，并加入 activity JNI 的 `BUILD.gn` 源集。
Java 薄桥沿现有 adapter framework jar 构建。设备包必须记录 source commit、
toolchain、target ABI、artifact SHA-256 和安装路径，禁止复用无法证明来源的旧产物。

## Test seams / 测试缝

host seam 注入确定性 owner、epoch、generation、transition、callback outcome、native
call outcome 和 first-frame receipt，覆盖正向、stale、duplicate、wrong-owner、
illegal-state、partial update、restart/replay。device seam 使用真实 OH callback、
真实 ApplicationThread/Activity callback、hilog 与 typed receipt；测试不得修改 APK
语义或以 probe 成功替代 callback。

## Rollback / 回滚

未发布的 core/bridge 变更可按 change manifest 隔离回退。已创建的 live registry
entry 必须先 typed revoke，再卸载新 adapter；不能通过恢复裸地址或 Java 双真源来
“回滚”。若 R1 无法保持 stock AOSP callback 或 native capability，则停止实现并
回到 Concept owner 裁决，而不是偷偷切到 R2。

## Oracle traceability / 判据追踪

- Positive：{item["positive"]}
- Negative：{item["negative"]}
- Failure：{item["failure"]}
- Evidence：输入/输出、状态前后、callback/ACK count、source/artifact hash 与设备身份
  必须能由 {evidence_join} 精确 join。

该设计冻结实现边界，但不声明 build、单元测试、真机测试或 Action PASS。
"""


def concept_design() -> str:
    rows = "\n".join(
        f"| `Fn03.{suffix}` | `{item['concept']}` | `{item['kind']}` | {item['intent']} | `DESIGN_READY_NOT_IMPLEMENTED` |"
        for suffix, item in ACTIONS.items()
    )
    return f"""# Fn03 Concept Design Handoff View

Status: `ACTION_DESIGN_FROZEN`

## 已选路线

R1 是已接受主方案：OH callback 进入 adapter boundary reducer，经 native
owner/generation-bound opaque token registry 关联到实例，再投递未修改的 AOSP
ClientTransaction/ActivityThread；terminal callback receipt 经 mapping/reducer 回到
OH。R2 lifecycle broker 是未来升级方案，不是自动备份路线。

## 公共对象与接口

共享类型为 `LifecycleEnvelope`、`LifecycleReceipt`、`OpaqueActivityCapability`、
`MappingDecision`、`TransitionLedger` 和 `FirstContentPresentReceipt`。所有对象均带
owner、process_epoch、generation、transition_id；裸地址、Intent、组件名和日志都
不能单独作为 live instance identity。

## 状态与生命周期实现边界

Fn03 只关联两侧状态真源。AOSP ATM/ActivityThread 仍拥有 Android lifecycle，
OH AbilityManager/UIAbilityThread 仍拥有 OH lifecycle。adapter 维护映射、幂等键、
typed receipt 和临时 join state，不建立第三套长期 lifecycle 真相。

## 构建与测试缝

纯 C++ core 提供 host unit-test seam；Java/JNI/OH ingress 提供真实边界 integration
seam；D200 真机以 stock APK callback、OH hilog、typed receipt 和首帧 producer
evidence 联合核验。host build 与 device build 的 ABI、commit 和 artifact hash
必须分别记录。

## Action 设计索引

| Action | 主 Concept | Kind | 独立行为 | 当前状态 |
|---|---|---|---|---|
{rows}

## 回滚与未来升级

R1 变更按 shared core、JNI、Java 薄桥和 handoff manifest 回滚；live capability
先撤销后卸载。R2 只有新增 falsifier evidence、独立评审和 owner 新裁决后才可启动，
不得用作 timeout fallback 或绕过 stock AOSP callback。

## Verification contract

每个 Action 固定 positive、negative、failure、raw evidence 与独立 replay。Action
PASS 不继承 Concept、依赖 Action、UI 或 Journey PASS；实现者不得担任最终 verifier。
`capability_bits` 是 Cr/Qy/Up/Dl/Ex/Ps/Cc/Is 的 one-hot 行为类型位，不是 Action
唯一编号；多个 `Ex` Action 使用相同 `0000-1000` 是预期分类，唯一性由 Action ID
与 capability_name 提供。
"""


def action_map_markdown() -> str:
    rows = "\n".join(
        f"| `Fn03.{suffix}` | `{item['concept']}` | `{item['kind']}` | `{item['bits']}` | "
        f"`{item['capability']}` | `READY` | {item['title']} |"
        for suffix, item in ACTIONS.items()
    )
    return f"""# Fn03 Action Map

Action ID 是稳定且唯一的独立核验边界；Concept 细化不得自动改号。

| Action | 主 Concept | 类型 | 类型位 | Capability | 契约状态 | 标题 |
|---|---|---|---|---|---|---|
{rows}

`capability_bits` 是 `Cr/Qy/Up/Dl/Ex/Ps/Cc/Is` 的 one-hot 类型位，不是 Action
唯一编号；同类 Action 共用类型位。Action 唯一性由 `Fn03.Ayy` 和
`capability_name` 提供。`READY` 只表示 contract/design 已冻结，不代表实现、
单元测试、真机测试或独立 verification 已通过。
"""


def main() -> None:
    (ROOT / "docs/spec/concepts/Fn03/lifecycle-mapping-v1.yaml").write_text(
        MAPPING_SCHEMA_TEXT, encoding="utf-8"
    )
    (ROOT / "docs/spec/concepts/Fn03/timeout-policy-v1.yaml").write_text(
        TIMEOUT_POLICY_TEXT, encoding="utf-8"
    )
    for suffix, item in ACTIONS.items():
        action_id = f"Fn03.{suffix}"
        spec = ROOT / "docs/spec/atoms/Fn03" / suffix
        (spec / "atom.yaml").write_text(
            yaml.safe_dump(atom_yaml(action_id, item), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        (spec / "verification.md").write_text(
            verification_text(action_id, item), encoding="utf-8"
        )
        (spec / "DESIGN_SPEC.md").write_text(
            design_text(action_id, item), encoding="utf-8"
        )

    action_map_path = ROOT / "docs/spec/concepts/Fn03/action-map.yaml"
    action_map = yaml.safe_load(action_map_path.read_text(encoding="utf-8"))
    for entry in action_map["actions"]:
        item = ACTIONS[entry["action_id"][-3:]]
        entry["capability_bits"] = item["bits"]
        entry["contract_status"] = "READY"
    action_map_path.write_text(
        yaml.safe_dump(action_map, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    concept_path = ROOT / "docs/spec/concepts/Fn03/concept.yaml"
    concept = yaml.safe_load(concept_path.read_text(encoding="utf-8"))
    concept["scope"] = (
        "覆盖 Fn03.A01-A10 的 callback、状态映射、token correlation、launch ingress、"
        "finish 终态和 first-frame gate；Action 设计服从已接受 R1。"
    )
    concept["non_goals"] = [
        "不修改 AOSP 或 OpenHarmony lifecycle 真源内部。",
        "不把 R2 lifecycle broker 当作自动 fallback。",
        "不以文档、构建、日志、进程存活或相邻 Action verdict 代替独立运行证据。",
    ]
    concept["status"] = "READY"
    concept_path.write_text(
        yaml.safe_dump(concept, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    (ROOT / "docs/concepts/Fn03/CONCEPT_DESIGN.md").write_text(
        concept_design(), encoding="utf-8"
    )
    (ROOT / "docs/concepts/Fn03/ACTION_MAP.md").write_text(
        action_map_markdown(), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
