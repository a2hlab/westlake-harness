#!/usr/bin/env python3
"""Adapt the prepass block in oh_adapter_install_apk_c_entry.cpp to the API the
full-src tree actually ships: PrepassBundleCodec::Encode (there is no
BuildInstallPrepass). Binding fields map from PrepassContextWire exactly as the
tree's own test fixture (install_packet_fixture.h) does. Idempotent.

Run ON hw248 against /opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve.
"""
from pathlib import Path

P = Path("/opt/build-runs/2026-09-28-oh6.1.0.31-bms-label-resolve/full-src/src/adapter"
         "/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp")
src = P.read_text()

OLD = """    oh_adapter::package_transaction::wire::PrepassBundleRecord prepass;
    if (!oh_adapter::BuildInstallPrepass(*context, apkSha256, artifacts,
        &prepass, &error) || !oh_adapter::WriteCanonicalPrepassFd(
        prepass.canonicalPayload, &plan->prepassFd)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        oh_adapter_close_game_install_plan(plan);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }"""

NEW = """    // Prepass bundle via the shipped codec (fixture-mapped binding fields).
    oh_adapter::package_transaction::PrepassBundle bundle;
    bundle.requestId = context->requestId;
    bundle.packageName = context->packageName;
    bundle.userId = context->userId;
    bundle.packageGeneration = context->candidateGeneration;
    bundle.apkDigest = apkSha256;
    bundle.contractDigest = context->contractSha256Hex;
    bundle.policyDigest = context->policySha256Hex;
    bundle.toolDigest = context->toolSha256Hex;
    bundle.topologyDigest = context->topologySha256Hex;
    bundle.runtimeGenerationSealDigest = context->runtimeGenerationSealSha256Hex;
    bundle.disposition = artifacts.empty()
        ? oh_adapter::package_transaction::PrepassDisposition::NO_NATIVE_ELF
        : oh_adapter::package_transaction::PrepassDisposition::HAS_NATIVE_ELF;
    bundle.nativeEntryCount = static_cast<uint32_t>(artifacts.size());
    for (const auto& artifact : artifacts) {
        if (artifact.elfFacts.has_value()) {
            bundle.elfFacts.push_back(*artifact.elfFacts);
        }
    }
    oh_adapter::package_transaction::wire::PrepassBundleRecord prepass;
    if (!oh_adapter::package_transaction::PrepassBundleCodec::Encode(
        bundle, &prepass, &error) || !oh_adapter::WriteCanonicalPrepassFd(
        prepass.canonicalPayload, &plan->prepassFd)) {
        oh_adapter::ApkVerifierClient::Close(&session);
        oh_adapter_close_game_install_plan(plan);
        return OH_ADAPTER_APK_VERIFY_PREPASS_FAILED;
    }"""

if "PrepassBundleCodec::Encode" in src and OLD not in src:
    print("already patched")
    raise SystemExit(0)
if OLD not in src:
    raise SystemExit("OLD prepass block not found — refusing blind patch")

src = src.replace(OLD, NEW, 1)
if '#include "prepass_bundle.h"' not in src:
    src = src.replace('#include "install_prepass_materializer.h"',
                      '#include "install_prepass_materializer.h"\n#include "prepass_bundle.h"', 1)
P.write_text(src)
print("patched OK")
