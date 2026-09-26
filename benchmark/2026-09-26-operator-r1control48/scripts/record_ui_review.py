from pathlib import Path
import sys,json
name,*images=sys.argv[1:];r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/r1control48'/name
for n in images:assert (r/n).is_file(),n
(r/'visual-review.json').write_text(json.dumps(dict(reviewed_images=images,reviewer='codex-2 screenshot inspection',true_feed=False,article_body=False,note='Selected screenshots show loading/empty feed or explicit network error; no visible article to tap. Tab switch and refresh attempts recorded in inputs.jsonl. This is functionality failure, not proof of its cause.'),indent=2))
