from pathlib import Path
import sys,json
name,activity,feed,body,title=sys.argv[1:6]
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/clamp48'/name
assert (r/feed).is_file() and (r/body).is_file()
p=r/'articles.json';items=json.loads(p.read_text()) if p.exists() else []
assert not any(a['body_image']==body for a in items)
items.append(dict(activity=activity,feed_image=feed,body_image=body,title=title,body_verified=True,method='manual inspection of actual screenshot plus anchored activity lifecycle'))
p.write_text(json.dumps(items,ensure_ascii=False,indent=2))
