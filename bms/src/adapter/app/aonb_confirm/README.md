# AonB Confirm HAP

Minimal OpenHarmony Stage-model HAP for the D600 manual button confirmation
protocol (`/opt/Bridge/docs/atoms/UI_CONFIRMATION_PROTOCOL.md`).

- **Bundle name:** `com.example.aonb.confirm`
- **Ability name:** `com.example.aonb.confirm.ConfirmActivity`
- **Target SDK:** OpenHarmony 6.1.0.105 / API 23 (matches D600 baseline)

## What it does

When started with the parameters below, the app shows a full-screen UI with:

- Action ID (e.g. `Fn01.A01`)
- Case ID (e.g. `P1` / `N1` / `F1`)
- Summary text
- A single **确认收到** button

Pressing the button creates the directory
`/data/local/tmp/aonb_confirm/<run-id>/<action>/` and writes a YAML file
`<case>.confirmed`.

## Build

Requires macOS with DevEco Studio and the OpenHarmony 6.1.0.105 SDK installed.

```bash
cd /opt/Bridge/src/adapter/app/aonb_confirm
AONB_SIGNING_PASSWORD='<local-ephemeral-password>' ./build.sh
```

The script:
1. Clones the read-only DevEco SDK to a writable `/tmp/ohos-sdk-mac/23`.
2. Builds the unsigned HAP with hvigor.
3. Generates a local debug certificate chain and signs the HAP.
4. Copies the signed HAP to `dist/aonb-confirm-default-signed.hap`.

> The self-signed certificate is intended only as a local packaging check and
> is not expected to be trusted by D600. For device deployment, use DevEco
> Studio auto-sign or an OpenHarmony device-bound debug profile. The signing
> password is supplied only through `AONB_SIGNING_PASSWORD`; it is never stored
> in this project.

## Install

With a device connected over hdc:

```bash
hdc -t <SERIAL> app install dist/aonb-confirm-default-signed.hap
```

If the device does not trust the self-signed certificate, install the debug
root CA first:

```bash
hdc -t <SERIAL> shell bm install -p signing/result/root-ca.cer
```

(or sign with DevEco auto-sign and reinstall).

## Start

```bash
hdc -t <SERIAL> shell aa start \
  -a com.example.aonb.confirm.ConfirmActivity \
  -b com.example.aonb.confirm \
  --es action Fn01.A01 \
  --es case P1 \
  --es summary "install success" \
  --es runId 20260725T120000Z-d600-5583-r1
```

The agent can then poll for the confirmation file:

```bash
hdc -t <SERIAL> shell \
  "test -f /data/local/tmp/aonb_confirm/20260725T120000Z-d600-5583-r1/Fn01.A01/P1.confirmed"
```

## Project layout

```
aonb_confirm/
├── AppScope/app.json5              # bundleName and app metadata
├── build-profile.json5             # SDK / product config
├── entry/
│   ├── src/main/module.json5       # ability declaration + permissions
│   ├── src/main/ets/entryability/ConfirmAbility.ets
│   └── src/main/ets/pages/Index.ets
├── signing/                        # local debug signing scripts
└── dist/                           # signed HAP output
```
