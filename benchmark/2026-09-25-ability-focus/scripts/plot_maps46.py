"""Host: plot exported resource samples without altering raw evidence."""
import csv,json,pathlib,re,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=pathlib.Path(sys.argv[1]);rows=list(csv.DictReader((r/'maps-curve.csv').open()))
valid=[x for x in rows if x['maps'] and x['rss_kib']]
t0=float(rows[0]['uptime']);x=[(float(a['uptime'])-t0)/60 for a in valid]
fig,axes=plt.subplots(2,1,figsize=(11,7),sharex=True,layout='constrained')
axes[0].plot(x,[int(a['maps']) for a in valid],label='Observed VMAs')
axes[0].axhline(65530,color='tab:red',linestyle='--',label='Old limit 65,530')
axes[0].set_ylabel('Mapping count');axes[0].legend(loc='upper left')
axes[0].set_title('Board 5ea34a45: max_map_count=1,048,576 (four patches)')
axes[1].plot(x,[int(a['rss_kib'])/1024 for a in valid],label='App RSS MiB')
axes[1].plot(x,[int(a['swap_kib'])/1024 for a in valid],label='App swap MiB')
axes[1].set_ylabel('MiB');axes[1].set_xlabel('Minutes since first sample');axes[1].legend(loc='upper left')
for p in sorted(r.glob('*-input.txt')):
 m=re.search(r'INPUT_BEFORE\n([\d.]+)',p.read_text())
 if not m:continue
 t=(float(m[1])-t0)/60
 for ax in axes:ax.axvline(t,color='gray',alpha=.35)
 axes[0].annotate(p.name.replace('-input.txt',''),(t,0),xycoords=('data','axes fraction'),xytext=(3,4),textcoords='offset points',rotation=90,fontsize=8)
for ax in axes:ax.grid(alpha=.2)
fig.savefig(r/'maps-curve.png',dpi=150);fig.savefig(r/'maps-curve.svg')
