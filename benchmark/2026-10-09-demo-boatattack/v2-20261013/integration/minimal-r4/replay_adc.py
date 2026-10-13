"""Exact offline byte replay of archived 9cc -> ADC; not a source build."""
import json,sys,tempfile,platform
from pathlib import Path
import prepare as p
import installer as i
HERE=Path(__file__).resolve().parent

def main():
 inputs=i.read(HERE/'adc-replay-inputs.json');base=p.pinned(inputs['baseline']);donor=p.pinned(inputs['candidate']);original=p.pinned(inputs['patch_table'])
 sequence=i.read(HERE/'adc-patch-sequence.json');i.need(sequence==i.read(original)['changes'],'patch sequence differs from pinned evidence')
 i.need(i.sha(base)==p.ANDROID_BASE and i.sha(donor)==p.ADC,'exact input pair')
 data=bytearray(base.read_bytes());i.need(len(sequence)==49,'49 bytes required');seen=set()
 for row in sequence:
  off=int(row['file_offset'],16);i.need(off not in seen and data[off]==row['before'],'duplicate offset/wrong preimage');seen.add(off);data[off]=row['after']
 with tempfile.TemporaryDirectory() as tmp:
  output=Path(tmp)/'libandroid.so';output.write_bytes(data)
  i.need(i.sha(output)==p.ADC and output.read_bytes()==donor.read_bytes(),'whole output differs')
  result={'status':'PASS_NEW_OFFLINE_BYTE_REPLAY_NOT_HISTORICAL_BUILD','python':platform.python_version(),'interpreter':p.pin(Path(sys.executable).resolve()),'inputs':inputs,'script_sha256':i.sha(Path(__file__)),'patch_sequence_sha256':i.sha(HERE/'adc-patch-sequence.json'),'patch_bytes':len(sequence),'output_sha256':i.sha(output),'output_bytes':output.stat().st_size,'full_byte_equal_to_archived_adc':True,'source_compile':False,'historical_execution_log_found':False,'board_calls':0}
 print(json.dumps(result,indent=2));return 0
if __name__=='__main__':sys.exit(main())
