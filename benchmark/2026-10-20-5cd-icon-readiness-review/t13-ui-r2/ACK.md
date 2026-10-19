# t13-ui-ready

SCOPED ACCEPT for commit54325371b, UI SHA623a703bc442d9d51b99ab06c8b04a6f6981bbf9d8e6472d7910c16798499e09. The final guard and selected icon click now share one remote shell; the inherited raw_shell marker is retained. Initial review/negative evidence is unchanged.

Five focused local cases passed using the exact UI class and real BMS Board.shell/raw_shell: success, STOP at dispatch, wrong state, lost reply, and awake failure. STOP/wrong state dispatch zero fixture clicks; unknown reply stays unknown; awake failure preserves the completed click. This closes the identified extra transport/ready gap, not every theoretical scheduling race. No device calls, no tool re-review, no old full-suite rerun.
