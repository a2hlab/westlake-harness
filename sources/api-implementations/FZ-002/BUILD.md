# Build and dependency boundary

Use `python3 build.py --generation /restored/generation --out /new/output` to print the original two compiler/link commands with explicit path relocation; append `--run` to build the delivered candidate unit. This executes no device command and writes only the new output tree. It keeps the original compiler flags and link inputs. It verifies the resulting provider against `0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c`; a mismatch is not silently accepted.

Source commit: `d8d7a3e0d911bee6549f01fc2234a85d6c23c30e`, identified by the original native freeze audit; blob `93382ec96d62caa5222e7c993af0098ed9096bb6`. Fetch the generation dependencies:
```bash
scp "$HW248_HOST:$HW248_HOME/westlake-oh6.1-b9-v3-74d1d6d4-source/build-inputs.tar.gz" .
scp "$HW248_HOST:$HW248_HOME/westlake-oh6.1-b9-v3-74d1d6d4-source/external-link-inputs.tar.gz" .
```
Verify `build-inputs.tar.gz` SHA `4e30856996917f44ba3442a11fd0e72558692a88fe7a96803ca1201b34fc19b9` and external-link SHA `93de93e057d103227b1606cd8f75f07d36f3661404585905cd3ec9cbbf1a7d11` from the copied original source-preservation and source-link-inputs receipts. The complete source manifest and compiler pin are retained. No dependency download or build was performed here.
