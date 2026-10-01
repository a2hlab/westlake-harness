spec: task
name: "Correlate completed sequential U8 BitVector logs with first fatal roots"
inherits: project
depends: [t1-classes]
---

## 意图

After all six sequential U8 pieces and the selected 5cd remainder complete, bind their app records and hilog, retain positive BitVector class evidence and compare independently found first fatal roots.

## 已定决策

- Refuse incomplete or overlapping cohorts and INVALID concurrent run directories for final full impact reporting.
- Admit the outer-selected six seq roots plus 5cd-seq-v1-rest; a later cleanup interruption does not erase a completed diagnostic and captured t20 receipt.
- Target PID only; garbageSetBits zero is a clean observation and foreign PID noise is excluded.
- Reuse first_fatal termination-first analysis; positive bits plus a root is only a suspected victim unless a causal class/stack or prior verified witness connects them.
- Hash raw logs and retain file/line/PID/TID/time coordinates; never convert missing logs or process-alive status into a clean verdict.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-libart-impact/**
- specs/b10-libart-impact/**
- tools/spec-checks/tests/b10_libart_impact.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Positive bits and terminal evidence stay distinct
  测试: b10_libart_bitvector
  假设 Positive target bits zero target bits a foreign PID and a terminal exception
  当 BitVector impact is classified
  那么 Only positive target bits enter the exposure list and fatal correlation never becomes an unproved cause

场景: Incomplete invalid and mismatched runtime runs are refused
  测试: b10_libart_runs
  假设 An incomplete cohort a concurrent invalid run or a wrong U8 identity
  当 Final full impact reporting admits inputs
  那么 Each invalid input is rejected and pending work is explicitly unverified

## 排除范围

- Diagnosing memory contents, modifying libart binaries, or claiming positive bits alone prove a crash.
