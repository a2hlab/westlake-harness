"""Save an explicit human/model visual review; never infer a body from log text."""
from pathlib import Path
import sys,json
name,feed,body,title=sys.argv[1:5]
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/hollow48'/name
assert (r/feed).is_file()
assert body=='none' or (r/body).is_file()
(r/'visual-review.json').write_text(json.dumps(dict(feed_real_titles=True,body_text_visible=body!='none',feed_image=feed,body_image=body,body_title=title,review_method='manual inspection of actual screenshot'),ensure_ascii=False,indent=2))
