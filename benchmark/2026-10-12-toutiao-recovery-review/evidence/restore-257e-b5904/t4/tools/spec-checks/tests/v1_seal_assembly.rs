// t6-sealpack: v1 seal assembly selectors. The real assembler is
// benchmark/2026-10-12-v1-seal-assembly/assemble.py; compile delegates to the
// pinned real t5 compiler (build_seal.build) — no self-invented seal format.
// Live on-site results enter only as parameters; missing/forged ones refuse.
use std::path::PathBuf;
use std::process::Command;

fn root() -> PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}
fn assembler() -> PathBuf {
    root().join("benchmark/2026-10-12-v1-seal-assembly/assemble.py")
}
fn run(args: &[&str]) -> (i32, String, String) {
    let out = Command::new("python3")
        .arg(assembler())
        .args(args)
        .current_dir(root())
        .output()
        .expect("run assembler");
    (
        out.status.code().unwrap_or(-1),
        String::from_utf8_lossy(&out.stdout).into_owned(),
        String::from_utf8_lossy(&out.stderr).into_owned(),
    )
}

#[test]
fn v1_seal_assembly_inventory() {
    let (code, stdout, stderr) = run(&["inventory"]);
    assert_eq!(code, 0, "inventory failed: {}", stderr);
    assert!(stdout.contains("BOARD_COMMANDS=0"));
    assert!(stdout.contains("PROVIDER order=1 id=u13-base"));
    assert!(stdout.contains("PROVIDER order=2 id=toutiao-route-b"));
    assert!(stdout.contains("RESTORE_ORDER"));
    assert!(stdout.contains("checked=10 pinned files, all digests match"));
    assert!(stdout.contains("sixty_one_b_20key manifest"));
    assert!(stdout.contains("five_cd_128_reference comparison"));
}

#[test]
fn v1_seal_assembly_reject() {
    let tmp = std::env::temp_dir().join("v1-seal-reject");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).unwrap();

    // (a) no live file at all: every required input named, nothing written
    let (code, _o, stderr) = run(&["compile"]);
    assert_ne!(code, 0);
    for key in ["live_snapshot_json", "interaction_signoff_json", "archive_sha256_map", "provider_admissions"] {
        assert!(stderr.contains(key), "must name {}: {}", key, stderr);
    }
    assert!(!root().join("benchmark/2026-10-12-v1-seal-assembly/seal.json").exists());

    // (b) outer's attack vector replayed verbatim + the strict-schema mutations
    let mut attack = String::from(concat!(
        r#"{"live_snapshot_json": "does/not/exist.json", "interaction_signoff_json": "","#,
        r#" "archive_sha256_map": {}, "provider_admissions": {"toutiao-route-b": {}}, "synthetic": false}"#
    ));
    std::fs::write(tmp.join("attack.json"), &attack).unwrap();
    let (code, _o, stderr) = run(&["compile", "--live", tmp.join("attack.json").to_str().unwrap(),
                                   "--out", tmp.join("fake-seal.json").to_str().unwrap()]);
    assert_ne!(code, 0, "forged material must be refused");
    assert!(!tmp.join("fake-seal.json").exists());

    // (c) mutation matrix over a valid synthetic base (built via the t5 fixture path)
    let build_base = Command::new("python3").arg("-c")
        .arg(concat!(
            "import json, sys, importlib.util, os, hashlib, tempfile;",
            "from pathlib import Path;",
            "T5 = os.environ['WORKSPACES'] + '/westlake-harness/benchmark/2026-10-09-demo-baseline/t5';",
            "sys.path.insert(0, T5);",
            "spec = importlib.util.spec_from_file_location('t5t', T5 + '/test_seal.py');",
            "t5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(t5);",
            "snap, overlays, manifest = t5.fixture(); snap['synthetic'] = True;",
            "td = Path(tempfile.mkdtemp(prefix='t6-rb-'));",
            "rb1, rb2 = td/'rb-u13.sh', td/'rb-toutiao.sh';",
            "rb1.write_text('# t6 rb'); rb2.write_text('# t6 rb');",
            "sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest();",
            "ev = td/'t6-step-evidence.txt'; ev.write_text('t6 step evidence');",
            "evsha = hashlib.sha256(ev.read_bytes()).hexdigest();",
            "steps = [{'name': n, 'passed': True, 'evidence': {'path': str(ev), 'sha256': evsha}} for n in ('launch','feed','refresh','article')];",
            "live = {'synthetic': True, 'live_snapshot_json': snap, 'overlays': overlays, 'manifest': manifest,",
            " 'interaction_signoff_json': {'accepted_by': 't6-fixture', 'steps': steps},",
            " 'archive_sha256_map': {'demo.apk': 'd'*64},",
            " 'provider_admissions': {",
            "   'u13-base': {'admitted_by': 't6-fixture', 'rollback': {'path': str(rb1), 'sha256': sha(rb1)}},",
            "   'toutiao-route-b': {'admitted_by': 't6-fixture', 'rollback': {'path': str(rb2), 'sha256': sha(rb2)}}}};",
            "open(sys.argv[1], 'w').write(json.dumps(live));",
        ))
        .arg(tmp.join("base.json"))
        .env("WORKSPACES", root().canonicalize().unwrap().parent().unwrap())
        .output().expect("build synthetic base");
    assert!(build_base.status.success(), "{}", String::from_utf8_lossy(&build_base.stderr));

    let mutations: Vec<(&str, String)> = vec![
        ("sign-steps-false", String::from(r#""steps": ["launch", "feed", "article"]"#)),
    ];
    let _ = mutations; // python-side mutations below keep the matrix in one place
    // mutation matrix via a helper script file (avoids one-liner separator pitfalls)
    let helper = tmp.join("mutate.py");
    std::fs::write(&helper, concat!(
        "import json, sys, subprocess, copy\n",
        "from pathlib import Path\n",
        "base = json.loads(Path(sys.argv[1]).read_text())\n",
        "muts = {\n",
        "  'sign-steps-false': lambda d: d['interaction_signoff_json'].update(steps=[False]),\n",
        "  'sign-steps-empty-str': lambda d: d['interaction_signoff_json'].update(steps=['']),\n",
        "  'archive-bad-sha': lambda d: d['archive_sha256_map'].update({'x': 'not-a-sha'}),\n",
        "  'provider-missing-u13': lambda d: d['provider_admissions'].pop('u13-base'),\n",
        "  'rollback-arbitrary-pair': lambda d: d['provider_admissions']['u13-base'].update(rollback={'x': 'y'}),\n",
        "  'rollback-wrong-sha': lambda d: d['provider_admissions']['toutiao-route-b']['rollback'].update(sha256='0'*64),\n",
        "  'lying-synthetic-false': lambda d: d.update(synthetic=False),\n",
        "}\n",
        "results = {}\n",
        "for name, fn in muts.items():\n",
        "    d = copy.deepcopy(base); fn(d)\n",
        "    lp = Path(sys.argv[2])/(name + '.json'); lp.write_text(json.dumps(d))\n",
        "    out = Path(sys.argv[2])/(name + '-out.json')\n",
        "    r = subprocess.run([sys.executable, sys.argv[3], 'compile', '--live', str(lp), '--out', str(out)], capture_output=True, text=True)\n",
        "    results[name] = {'rc': r.returncode, 'wrote': out.exists()}\n",
        "print(json.dumps(results))\n",
    )).unwrap();
    let matrix = Command::new("python3")
        .arg(&helper)
        .arg(tmp.join("base.json"))
        .arg(&tmp)
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/assemble.py"))
        .output().expect("run mutation matrix");
    let out = String::from_utf8_lossy(&matrix.stdout);
    assert!(matrix.status.success(), "{}", String::from_utf8_lossy(&matrix.stderr));
    for name in ["sign-steps-false", "sign-steps-empty-str", "archive-bad-sha", "provider-missing-u13",
                 "rollback-arbitrary-pair", "rollback-wrong-sha", "lying-synthetic-false"] {
        let pat = format!(r#""{}": {{"rc": 2, "wrote": false}}"#, name);
        assert!(out.contains(&pat), "mutation {} must refuse rc=2 and write nothing: {}", name, out);
    }
}

#[test]
fn v1_seal_assembly_fixture() {
    let tmp = std::env::temp_dir().join("v1-seal-fixture");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).unwrap();

    // (a) drifted manifest SHA on an isolated inputs copy -> inventory refuses
    let drift = Command::new("python3").arg("-c")
        .arg("import json,sys;d=json.load(open(sys.argv[1]));d['sixty_one_b_20key']['manifest']['sha256']='0'*64;open(sys.argv[2],'w').write(json.dumps(d))")
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/assembly-inputs.json"))
        .arg(tmp.join("drifted-inputs.json"))
        .output().expect("drift fixture");
    assert!(drift.status.success());
    let (code, _o, e) = run(&["inventory", "--inputs", tmp.join("drifted-inputs.json").to_str().unwrap()]);
    assert_ne!(code, 0);
    assert!(e.contains("SHA drift manifest"), "{}", e);

    // (b) real t5 fixture material compiles through the pinned t5 compiler and
    // produces a REAL demo-seal/v1 with BOTH providers, real rollback files,
    // synthetic provenance preserved, and an assembly receipt bound to the seal
    let make_live = Command::new("python3").arg("-c")
        .arg(concat!(
            "import json, sys, importlib.util, os, hashlib, tempfile;",
            "from pathlib import Path;",
            "T5 = os.environ['WORKSPACES'] + '/westlake-harness/benchmark/2026-10-09-demo-baseline/t5';",
            "sys.path.insert(0, T5);",
            "spec = importlib.util.spec_from_file_location('t5t', T5 + '/test_seal.py');",
            "t5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(t5);",
            "snap, overlays, manifest = t5.fixture(); snap['synthetic'] = True;",
            "td = Path(tempfile.mkdtemp(prefix='t6-rb-fx'));",
            "rb1, rb2 = td/'rb-u13.sh', td/'rb-toutiao.sh';",
            "rb1.write_text('# t6 rb'); rb2.write_text('# t6 rb');",
            "sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest();",
            "ev = td/'t6-step-evidence.txt'; ev.write_text('t6 step evidence');",
            "evsha = hashlib.sha256(ev.read_bytes()).hexdigest();",
            "steps = [{'name': n, 'passed': True, 'evidence': {'path': str(ev), 'sha256': evsha}} for n in ('launch','feed','refresh','article')];",
            "live = {'synthetic': True, 'live_snapshot_json': snap, 'overlays': overlays, 'manifest': manifest,",
            " 'interaction_signoff_json': {'accepted_by': 't6-fixture', 'steps': steps},",
            " 'archive_sha256_map': {'demo.apk': 'd'*64},",
            " 'provider_admissions': {",
            "   'u13-base': {'admitted_by': 't6-fixture', 'rollback': {'path': str(rb1), 'sha256': sha(rb1)}},",
            "   'toutiao-route-b': {'admitted_by': 't6-fixture', 'rollback': {'path': str(rb2), 'sha256': sha(rb2)}}}};",
            "open(sys.argv[1], 'w').write(json.dumps(live));",
        ))
        .arg(tmp.join("live.json"))
        .env("WORKSPACES", root().canonicalize().unwrap().parent().unwrap())
        .output().expect("build t5 fixture live set");
    assert!(make_live.status.success(), "{}", String::from_utf8_lossy(&make_live.stderr));

    let (code, stdout, stderr) = run(&["compile", "--live", tmp.join("live.json").to_str().unwrap(),
                                       "--out", tmp.join("seal.json").to_str().unwrap()]);
    assert_eq!(code, 0, "complete t5-fixture material must compile via the real compiler: {}", stderr);
    assert!(stdout.contains("real demo-seal/v1 via t5 build_seal.build"), "{}", stdout);
    assert!(stdout.contains("assembly receipt bound to seal sha"), "{}", stdout);
    let body = std::fs::read_to_string(tmp.join("seal.json")).unwrap();
    let v: serde_json_shim::Value = serde_json_shim::parse(&body);
    assert_eq!(v.get("schema").as_deref(), Some("demo-seal/v1"));
    assert_eq!(v.get("synthetic").as_deref(), Some("true"), "synthetic must stay marked");
    assert_eq!(v.get("serial").as_deref(), Some("61b0657200000000000000000324012c"));
    let receipt = std::fs::read_to_string(tmp.join("seal-assembly-receipt.json")).unwrap();
    let r: serde_json_shim::Value = serde_json_shim::parse(&receipt);
    assert!(r.get("seal_sha256").is_some(), "receipt binds the seal digest");
    assert!(receipt.contains("u13-base") && receipt.contains("toutiao-route-b"), "receipt carries both providers");
    // and it never lands in the assembly directory
    assert!(!root().join("benchmark/2026-10-12-v1-seal-assembly/seal.json").exists());
}

// minimal JSON shim so this test file needs no new cargo dependencies
mod serde_json_shim {
    pub struct Value(String);
    impl Value {
        pub fn get(&self, key: &str) -> Option<String> {
            let pat = format!("\"{}\":", key);
            let body = &self.0;
            let idx = body.find(&pat)?;
            let rest = body[idx + pat.len()..].trim_start();
            if rest.starts_with('"') {
                let end = rest[1..].find('"')? + 1;
                Some(rest[1..end].to_string())
            } else {
                let end = rest.find([',', '\n', '}'])?;
                Some(rest[..end].trim().to_string())
            }
        }
    }
    pub fn parse(s: &str) -> Value {
        Value(s.to_string())
    }
}

#[test]
fn v1_seal_assembly_deployment() {
    let tmp = std::env::temp_dir().join("v1-seal-deployment");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).unwrap();

    // build the synthetic seal + candidate deployment with the same shape the
    // python-side harness used (real t5 build + real source files)
    let build = Command::new("python3").arg("-c")
        .arg(concat!(
            "import json, sys, importlib.util, os, hashlib, tempfile;\n",
            "from pathlib import Path;\n",
            "T5 = os.environ['WORKSPACES'] + '/westlake-harness/benchmark/2026-10-09-demo-baseline/t5';\n",
            "sys.path.insert(0, T5);\n",
            "spec = importlib.util.spec_from_file_location('t5t', T5 + '/test_seal.py');\n",
            "t5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(t5);\n",
            "import build_seal;\n",
            "td = Path(tempfile.mkdtemp(prefix='t6-dep-rs-'));\n",
            "sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest();\n",
            "S = {};\n",
            "for k in ('runtime','boot','installer','apk','tt','rb-u13','rb-tt','prog-u13','prog-tt'):\n",
            "    p = td/(k+'.bin'); p.write_bytes(k.encode()*7); S[k] = p;\n",
            "snap, overlays, manifest = t5.fixture(); snap['synthetic'] = True;\n",
            "apk_path = '/data/app/el1/bundle/public/org.demo/android/base.apk';\n",
            "tt_path = '/data/app/el1/bundle/public/org.westlake.imehost/haps/entry/ttbundle.bin';\n",
            "snap['files'] = {'runtime': {'/system/android/lib64/liboh_android_runtime.so': sha(S['runtime'])},\n",
            " 'boot': {'/system/android/framework/arm64/boot.art': sha(S['boot'])},\n",
            " 'installation': {'/system/lib64/libinstalls.z.so': sha(S['installer'])},\n",
            " 'overlays': {tt_path: sha(S['tt'])}};\n",
            "snap['fingerprint_lines'] = {g: [sha(S[k]) + '  ' + list(snap['files'][g])[0]] for g, k in (('runtime','runtime'), ('boot','boot'))};\n",
            "snap['packages'] = [\n",
            " {'package': 'org.demo', 'version_code': 3, 'version_name': '1.0', 'apk_path': apk_path, 'apk_sha256': sha(S['apk'])},\n",
            " {'package': 'org.westlake.imehost', 'version_code': 1, 'version_name': '1.0', 'apk_path': '/data/app/el1/bundle/public/org.westlake.imehost/base.apk', 'apk_sha256': sha(S['tt'])}];\n",
            "snap['apk_hashes'] = {p['apk_path']: p['apk_sha256'] for p in snap['packages']};\n",
            "snap['inventories'] = [{'patterns': ['/system/android/lib64/*.so'], 'paths': ['/system/android/lib64/liboh_android_runtime.so']}];\n",
            "overlays = {'schema': 'demo-overlays/v1', 'seal_stage': 'v1', 'items': [\n",
            " {'id': 'toutiao-route-b', 'route': 'B', 'state': 'active', 'package': 'com.ss.android.article.news',\n",
            "  'apk_sha256': sha(S['tt']), 'version_name': '1.0', 'version_code': 1, 'launch_kind': 'embedded-in-hap',\n",
            "  'host_package': 'org.westlake.imehost', 'payload_path': tt_path,\n",
            "  'files': [{'target': tt_path, 'sha256': sha(S['tt']), 'role': 'ttbundle'}],\n",
            "  'source': {'path': str(S['tt']), 'sha256': sha(S['tt'])},\n",
            "  'rollback': {'path': str(S['rb-tt']), 'sha256': sha(S['rb-tt'])}},\n",
            " {'id': 'boatattack', 'state': 'absent', 'reason': 'v1 no Boat', 'files': []}]};\n",
            "manifest['apps'] = [dict(manifest['apps'][0], apk_sha256=sha(S['apk']))];\n",
            "seal = build_seal.build(snap, overlays, manifest); seal['synthetic'] = True;\n",
            "json.dump(seal, open(sys.argv[1], 'w'), indent=1);\n",
            "expected = {};\n",
            "for members in seal['files'].values(): expected.update(members);\n",
            "for pkg in seal['packages']: expected[pkg['apk_path']] = pkg['apk_sha256'];\n",
            "srcmap = {'/system/android/lib64/liboh_android_runtime.so': 'runtime.bin', '/system/android/framework/arm64/boot.art': 'boot.bin',\n",
            " '/system/lib64/libinstalls.z.so': 'installer.bin', apk_path: 'apk.bin', tt_path: 'tt.bin',\n",
            " '/data/app/el1/bundle/public/org.westlake.imehost/base.apk': 'tt.bin'};\n",
            "dep_files = [{'target': t, 'mode': 'restore', 'source': {'path': str(srcmap[t]), 'sha256': expected[t]}} for t in sorted(expected)];\n",
            "deployment = {'schema': 'demo-restore-deployment/v1', 'execution_enabled': False, 'synthetic': True, 'files': dep_files,\n",
            " 'providers': [\n",
            "  {'layer': 'u13', 'interpreter': 'bash', 'program': {'path': 'prog-u13.bin', 'sha256': sha(S['prog-u13'])},\n",
            "   'rollback': {'path': 'rb-u13.bin', 'sha256': sha(S['rb-u13'])},\n",
            "   'targets': sorted(t for t in expected if t != tt_path)},\n",
            "  {'layer': 'toutiao-route-b', 'interpreter': 'bash', 'program': {'path': 'prog-tt.bin', 'sha256': sha(S['prog-tt'])},\n",
            "   'rollback': {'path': 'rb-tt.bin', 'sha256': sha(S['rb-tt'])}, 'targets': [tt_path]}]};\n",
            "json.dump(deployment, open(td/'candidate.json', 'w'), indent=1);\n",
            "open(sys.argv[1], 'w').write(str(td/'candidate.json'));\n",
            "json.dump(seal, open(sys.argv[2], 'w'), indent=1);\n",
        ))
        .arg(tmp.join("marker.txt"))
        .arg(tmp.join("seal.json"))
        .arg(tmp.join("unused.json"))
        .env("WORKSPACES", root().canonicalize().unwrap().parent().unwrap())
        .output().expect("build seal+deployment fixture");
    assert!(build.status.success(), "{}", String::from_utf8_lossy(&build.stderr));

    // (a) valid candidate assembles via the REAL t5 restore.validate
    // fixture wrote the candidate next to its .bin sources in td and left the
    // plain-text path in marker.txt
    let candidate_in_td = std::path::PathBuf::from(
        std::fs::read_to_string(tmp.join("marker.txt")).unwrap().trim().to_string());
    let (code, stdout, stderr) = run(&["assemble-deployment", "--seal", tmp.join("seal.json").to_str().unwrap(),
                                       "--deployment", candidate_in_td.to_str().unwrap(),
                                       "--out", tmp.join("ok").to_str().unwrap()]);
    assert_eq!(code, 0, "valid deployment must assemble: {}", stderr);
    assert!(stdout.contains("validated by real t5 restore.validate"), "{}", stdout);
    assert!(stdout.contains("execution_enabled stays false"), "{}", stdout);
    let receipt = std::fs::read_to_string(tmp.join("ok/restore-assembly-receipt.json")).unwrap();
    assert!(receipt.contains("v1-restore-assembly-receipt/1"));
    assert!(receipt.contains("t5 restore.validate(seal, deployment, base)"));
    let dep_out = std::fs::read_to_string(tmp.join("ok/restore-deployment.json")).unwrap();
    assert!(dep_out.contains("\"execution_enabled\": false"));

    // (b) mutation negatives: each refuses rc=2 and writes nothing
    let helper = tmp.join("mut.py");
    std::fs::write(&helper, concat!(
        "import json, sys, subprocess, copy;\n",
        "from pathlib import Path;\n",
        "dep = json.loads(Path(sys.argv[1]).read_text());\n",
        "muts = {\n",
        "  'pending-providers-empty': lambda d: d.update(providers=[]),\n",
        "  'wrong-layer-id': lambda d: d['providers'][0].update(layer='toutiao-route-b'),\n",
        "  'only-toutiao-no-u13': lambda d: d['providers'].pop(0),\n",
        "  'source-sha-mismatch': lambda d: d['files'][0]['source'].update(sha256='0'*64),\n",
        "  'missing-target-coverage': lambda d: d['files'].pop(),\n",
        "  'arrives-enabled': lambda d: d.update(execution_enabled=True),\n",
        "};\n",
        "results = {};\n",
        "for name, fn in muts.items():\n",
        "    d = copy.deepcopy(dep); fn(d);\n",
        "    dp = Path(sys.argv[1]).parent/(name+'.json'); dp.write_text(json.dumps(d));\n",
        "    outd = Path(sys.argv[2])/(name+'-out');\n",
        "    r = subprocess.run([sys.executable, sys.argv[3], 'assemble-deployment', '--seal', sys.argv[4], '--deployment', str(dp), '--out', str(outd)], capture_output=True, text=True);\n",
        "    results[name] = {'rc': r.returncode, 'wrote': (outd/'restore-deployment.json').exists() if outd.exists() else False};\n",
        "print(json.dumps(results));\n",
    )).unwrap();
    let matrix = Command::new("python3")
        .arg(&helper)
        .arg(std::fs::read_to_string(tmp.join("marker.txt")).unwrap().trim().to_string())
        .arg(&tmp)
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/assemble.py"))
        .arg(tmp.join("seal.json"))
        .output().expect("run deployment mutation matrix");
    let out = String::from_utf8_lossy(&matrix.stdout);
    assert!(matrix.status.success(), "{}", String::from_utf8_lossy(&matrix.stderr));
    for name in ["pending-providers-empty", "wrong-layer-id", "only-toutiao-no-u13",
                 "source-sha-mismatch", "missing-target-coverage", "arrives-enabled"] {
        let pat = format!(r#""{}": {{"rc": 2, "wrote": false}}"#, name);
        assert!(out.contains(&pat), "mutation {} must refuse rc=2 and write nothing: {}", name, out);
    }
}

#[test]
fn v1_seal_assembly_providers() {
    let tmp = std::env::temp_dir().join("v1-seal-providers");
    let _ = std::fs::remove_dir_all(&tmp);
    std::fs::create_dir_all(&tmp).unwrap();

    // build seal + mirrored archive index + route-b executor param (same shape as the python harness)
    let build = Command::new("python3").arg("-c")
        .arg(concat!(
            "import json, sys, importlib.util, os, hashlib, tempfile, shutil;\n",
            "from pathlib import Path;\n",
            "T5 = os.environ['WORKSPACES'] + '/westlake-harness/benchmark/2026-10-09-demo-baseline/t5';\n",
            "sys.path.insert(0, T5);\n",
            "spec = importlib.util.spec_from_file_location('t5t', T5 + '/test_seal.py');\n",
            "t5 = importlib.util.module_from_spec(spec); spec.loader.exec_module(t5);\n",
            "import build_seal;\n",
            "td = Path(tempfile.mkdtemp(prefix='t6-prov-rs-'));\n",
            "sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest();\n",
            "S = {};\n",
            "for k in ('runtime','boot','installer','apk','tt','rb-tt','prog-tt'):\n",
            "    p = td/(k+'.bin'); p.write_bytes(k.encode()*7); S[k] = p;\n",
            "snap, overlays, manifest = t5.fixture(); snap['synthetic'] = True;\n",
            "apk_path = '/data/app/el1/bundle/public/org.demo/android/base.apk';\n",
            "tt_path = '/data/app/el1/bundle/public/org.westlake.imehost/haps/entry/ttbundle.bin';\n",
            "snap['files'] = {'runtime': {'/system/android/lib64/liboh_android_runtime.so': sha(S['runtime'])},\n",
            " 'boot': {'/system/android/framework/arm64/boot.art': sha(S['boot'])},\n",
            " 'installation': {'/system/lib64/libinstalls.z.so': sha(S['installer'])},\n",
            " 'overlays': {tt_path: sha(S['tt'])}};\n",
            "snap['fingerprint_lines'] = {g: [sha(S[k]) + '  ' + list(snap['files'][g])[0]] for g, k in (('runtime','runtime'), ('boot','boot'))};\n",
            "snap['packages'] = [\n",
            " {'package': 'org.demo', 'version_code': 3, 'version_name': '1.0', 'apk_path': apk_path, 'apk_sha256': sha(S['apk'])},\n",
            " {'package': 'org.westlake.imehost', 'version_code': 1, 'version_name': '1.0', 'apk_path': '/data/app/el1/bundle/public/org.westlake.imehost/base.apk', 'apk_sha256': sha(S['tt'])}];\n",
            "snap['apk_hashes'] = {p['apk_path']: p['apk_sha256'] for p in snap['packages']};\n",
            "snap['inventories'] = [{'patterns': ['/system/android/lib64/*.so'], 'paths': ['/system/android/lib64/liboh_android_runtime.so']}];\n",
            "overlays = {'schema': 'demo-overlays/v1', 'seal_stage': 'v1', 'items': [\n",
            " {'id': 'toutiao-route-b', 'route': 'B', 'state': 'active', 'package': 'com.ss.android.article.news',\n",
            "  'apk_sha256': sha(S['tt']), 'version_name': '1.0', 'version_code': 1, 'launch_kind': 'embedded-in-hap',\n",
            "  'host_package': 'org.westlake.imehost', 'payload_path': tt_path,\n",
            "  'files': [{'target': tt_path, 'sha256': sha(S['tt']), 'role': 'ttbundle'}],\n",
            "  'source': {'path': 'tt.bin', 'sha256': sha(S['tt'])},\n",
            "  'rollback': {'path': 'rb-tt.bin', 'sha256': sha(S['rb-tt'])}},\n",
            " {'id': 'boatattack', 'state': 'absent', 'reason': 'v1 no Boat', 'files': []}]};\n",
            "manifest['apps'] = [dict(manifest['apps'][0], apk_sha256=sha(S['apk']))];\n",
            "seal = build_seal.build(snap, overlays, manifest); seal['synthetic'] = True;\n",
            "json.dump(seal, open(sys.argv[1], 'w'), indent=1);\n",
            "expected = {};\n",
            "for members in seal['files'].values(): expected.update(members);\n",
            "for pkg in seal['packages']: expected[pkg['apk_path']] = pkg['apk_sha256'];\n",
            "srcmap = {'/system/android/lib64/liboh_android_runtime.so': S['runtime'], '/system/android/framework/arm64/boot.art': S['boot'],\n",
            " '/system/lib64/libinstalls.z.so': S['installer'], apk_path: S['apk'], tt_path: S['tt'],\n",
            " '/data/app/el1/bundle/public/org.westlake.imehost/base.apk': S['tt']};\n",
            "files_idx = [];\n",
            "for t in sorted(expected):\n",
            "    p = td/('archive-' + t.replace('/', '_')); shutil.copy2(srcmap[t], p);\n",
            "    files_idx.append({'target': t, 'source': str(p), 'sha256': expected[t], 'bytes': p.stat().st_size, 'cached': True});\n",
            "json.dump({'serial': '61b0657200000000000000000324012c', 'source_kind': 'synthetic mirror', 'files': files_idx,\n",
            " 'bytes': sum(f['bytes'] for f in files_idx)}, open(sys.argv[2], 'w'));\n",
            "rb = {'path': str(S['prog-tt']), 'sha256': sha(S['prog-tt']), 'interpreter': 'bash',\n",
            " 'rollback': {'path': str(S['rb-tt']), 'sha256': sha(S['rb-tt'])}};\n",
            "json.dump(rb, open(sys.argv[3], 'w'));\n",
            "open(sys.argv[4], 'w').write(str(td));\n",
        ))
        .arg(tmp.join("seal.json"))
        .arg(tmp.join("index.json"))
        .arg(tmp.join("rb.json"))
        .arg(tmp.join("td.txt"))
        .env("WORKSPACES", root().canonicalize().unwrap().parent().unwrap())
        .output().expect("build provider fixture");
    assert!(build.status.success(), "{}", String::from_utf8_lossy(&build.stderr));
    let td = std::fs::read_to_string(tmp.join("td.txt")).unwrap().trim().to_string();

    // (a) without route-b executor: candidate builds with pending; assemble refuses
    let out = Command::new("python3")
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/providers.py"))
        .arg("--seal").arg(tmp.join("seal.json"))
        .arg("--index").arg(tmp.join("index.json"))
        .arg("--out").arg(tmp.join("cand-pending.json"))
        .current_dir(root()).output().expect("providers pending run");
    assert!(out.status.success());
    let cand = std::fs::read_to_string(tmp.join("cand-pending.json")).unwrap();
    assert!(cand.contains("toutiao-route-b executor (t0 parameter: path+sha256+rollback)"), "{}", cand);
    let asm = Command::new("python3")
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/assemble.py"))
        .arg("assemble-deployment")
        .arg("--seal").arg(tmp.join("seal.json"))
        .arg("--deployment").arg(tmp.join("cand-pending.json"))
        .arg("--out").arg(tmp.join("assembled-pending"))
        .current_dir(root()).output().expect("assemble pending");
    assert!(!asm.status.success(), "pending route-b must refuse assembly");
    assert!(String::from_utf8_lossy(&asm.stderr).contains("REFUSED pending"));

    // An explicit reviewed U13 profile is required; Route B alone is insufficient.
    let profile = Command::new("python3").arg("-c")
        .arg("import json,sys;from pathlib import Path;r=json.load(open(sys.argv[1]));pin={'path':r['path'],'sha256':r['sha256']};d={'executor':pin,'rollback':r['rollback'],'boot_id':'43bc3915-04bd-42ca-895e-26e8292911fa','serial':'5cd1e3dd00000000000000000923012c','transport':{'lane':'fixture','hdc_cmd':'NEVER','lock_cmd':'NEVER'},'apk_install':{'executor':pin,'entry':pin,'manifest':pin,'input_root':str(Path(sys.argv[1]).parent),'keys':['fixture']}};json.dump(d,open(sys.argv[2],'w'))")
        .arg(tmp.join("rb.json")).arg(tmp.join("u13-profile.json"))
        .output().unwrap();
    assert!(profile.status.success());
    // (b) with both reviewed profiles: structural chain through real t5 validate
    let out = Command::new("python3")
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/providers.py"))
        .arg("--seal").arg(tmp.join("seal.json"))
        .arg("--index").arg(tmp.join("index.json"))
        .arg("--route-b-executor").arg(tmp.join("rb.json"))
        .arg("--u13-profile").arg(tmp.join("u13-profile.json"))
        .arg("--out").arg(format!("{}/cand-ok.json", td))
        .current_dir(root()).output().expect("providers ok run");
    assert!(out.status.success(), "{}", String::from_utf8_lossy(&out.stderr));
    let asm = Command::new("python3")
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/assemble.py"))
        .arg("assemble-deployment")
        .arg("--seal").arg(tmp.join("seal.json"))
        .arg("--deployment").arg(format!("{}/cand-ok.json", td))
        .arg("--out").arg(tmp.join("assembled-ok"))
        .current_dir(root()).output().expect("assemble ok");
    assert!(asm.status.success(), "{}", String::from_utf8_lossy(&asm.stderr));
    let receipt = std::fs::read_to_string(tmp.join("assembled-ok/restore-assembly-receipt.json")).unwrap();
    assert!(receipt.contains("\"execution_enabled\": false"));
    let dep = std::fs::read_to_string(tmp.join("assembled-ok/restore-deployment.json")).unwrap();
    assert!(dep.contains("\"layer\": \"u13\"") && dep.contains("\"layer\": \"toutiao-route-b\""));
    // U13 provider pins the real verified programs
    assert!(dep.contains("u13_provider.py"));
    assert!(dep.contains("apk_provider.py"));
}

fn provider_case(name: &str) {
    let output = Command::new("python3")
        .arg(root().join("benchmark/2026-10-12-v1-seal-assembly/test_provider_execution.py"))
        .arg(name)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root()).output().expect("isolated provider execution");
    assert!(output.status.success(), "{}", String::from_utf8_lossy(&output.stderr));
}

#[test]
fn v1_seal_assembly_u13_provider_typed() {
    provider_case("ProviderExecution.test_u13_ready_baseline_skips_replay_and_dispatches_apk");
    provider_case("ProviderExecution.test_u13_self_pin_refuses_before_board");
    provider_case("ProviderExecution.test_u13_executor_drift_refuses_before_board");
}

#[test]
fn v1_seal_assembly_apk_provider() {
    provider_case("ProviderExecution");
}
