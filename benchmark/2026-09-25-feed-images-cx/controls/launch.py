import sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from launch30 import launch
r,d=launch(sys.argv[1],"baseline",app=sys.argv[2]);print("READY",d["child"],flush=True)
