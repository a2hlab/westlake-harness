from pathlib import Path
import re
R=Path(__file__).resolve().parents[2];A=R/'bms/src/.work/b68-generation/adapter';S=A/'framework/appspawn-x/security_specialization/stock_child_plugin/src'
p=S/'westlake_stock_host_main.c';s=p.read_text()
for macro in ['WLASC_PLUGIN_ELF_SHA256_HEX','WLASC_PLUGIN_BUILD_ID_HEX']:
 s=re.sub(r'#ifndef '+macro+r'\n#error [^\n]+\n#endif\n','',s)
s=s.replace('    static const char plugin_build_id_hex[] = WLASC_PLUGIN_BUILD_ID_HEX;\n','').replace('    static const char plugin_elf_sha_hex[] =\n        WLASC_PLUGIN_ELF_SHA256_HEX;\n','')
s=s.replace('''        FillHex(services.plugin_elf_sha256,
                sizeof(services.plugin_elf_sha256),
                plugin_elf_sha_hex,
                sizeof(plugin_elf_sha_hex)) != 0 ||
        FillHex(services.plugin_build_id,
                sizeof(services.plugin_build_id),
                plugin_build_id_hex,
                sizeof(plugin_build_id_hex)) != 0''','''        0 /* plugin file identity fields remain zero; ABI slots retained */''')
p.write_text(s)
p=S/'westlake_android_child_plugin.c';s=p.read_text();s=s.replace('    static const char plugin_build_id_hex[] = WLASC_PLUGIN_BUILD_ID_HEX;\n','')
s=s.replace('''        !BytesAllZero(services->plugin_elf_sha256,
                      sizeof(services->plugin_elf_sha256)) &&
        BytesMatchHex(services->plugin_build_id,
                      WLASC_BUILD_ID_SIZE, plugin_build_id_hex,
                      sizeof(plugin_build_id_hex)) &&
''','''        /* #68: no file SHA/build-id admission for the child plugin. */
''');p.write_text(s)
