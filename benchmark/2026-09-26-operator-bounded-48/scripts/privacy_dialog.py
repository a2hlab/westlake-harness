"""Fixed-device visual gate for this authorized consent dialog, not a general UI recognizer."""
from PIL import Image

def privacy_dialog(path):
 im=Image.open(path).convert('RGB')
 if im.size!=(1200,1920):return False
 def all_pixels(points,predicate):return all(predicate(*im.getpixel(p)) for p in points)
 return (all_pixels([(340,1250),(400,1250),(800,1295),(850,1295)],lambda r,g,b:r>235 and 30<g<100 and 20<b<110)
  and all_pixels([(320,850),(880,1150),(320,800),(880,800)],lambda r,g,b:min(r,g,b)>247)
  and all_pixels([(580,720),(610,705)],lambda r,g,b:85<r<160 and 140<g<210 and b>225 and b-r>65))
