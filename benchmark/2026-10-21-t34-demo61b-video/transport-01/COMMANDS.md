# W-02 command prefix

Use the unchanged original T34 argument list and the **new W-02 holder/start/admission**.
`D` is the original deployment directory, `T` this `transport-01` directory.

```sh
python3 "$T/file_transport.py" --executor "$D/executor61b.py" -- preflight <original exact preflight arguments>
python3 "$T/file_transport.py" --executor "$D/executor61b.py" -- apply <original exact apply arguments>
python3 "$T/file_transport.py" --executor "$D/executor61b.py" -- rollback <original exact rollback arguments>
```

These lines describe the prefix; `<...>` must be replaced by the reviewed original arguments.
Complete concrete-variable examples are in `README.md`. Use it for both apply and
rollback; do not reset W-01 or borrow its plan. No source/admission pin changes.
The original `--execute` remains required. Unknown write status never auto-retries.
