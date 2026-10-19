"""Offline materials; layout conventions adapted from 2026-10-08-lit-apps-gallery/build_pptx.py."""
import json, sys, math, re
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
HERE=Path(__file__).resolve().parent; OUT=HERE/'delivery'
DATA=json.loads((OUT/'manifest.json').read_text()); ROWS=DATA['rows']; BY={r['key']:r for r in ROWS}
FONT='PingFang SC'; BG='101B2B'; FG='F4F7FB'; MUTED='AAB9CC'; ACCENT='4BC6B5'
SELECTED=['toutiao-route-b','boatattack','cv2-com-kaajjo-libresudoku','cv2-com-darkempire78-opencalculator','cv2-com-better-alarm','cv2-com-chess-clock','cv2-com-tomatodev-timerdroid','cv2-de-markusfisch-android-shadereditor','cv2-org-secuso-privacyfriendlydicer','fd-mpv','cv2-com-groce-app','fd-etar','fd-com-amaze-filemanager','cv2-com-nicue-onetwo','cv2-com-vonglasow-michael-voltagedrop','cv2-org-secuso-privacyfriendlyruler']
ALIASES={'cv2-com-darkempire78-opencalculator':'OpenCalc','cv2-com-better-alarm':'Better Alarm','cv2-com-chess-clock':'Chess Clock','cv2-com-tomatodev-timerdroid':'TimerDroid','cv2-de-markusfisch-android-shadereditor':'Shader Editor','cv2-org-secuso-privacyfriendlydicer':'Dice','fd-mpv':'mpv-android','cv2-com-groce-app':'Groce','fd-etar':'Etar 日历','fd-com-amaze-filemanager':'Amaze 文件管理器','cv2-com-nicue-onetwo':'OneTwo','cv2-com-vonglasow-michael-voltagedrop':'Voltage Drop','cv2-org-secuso-privacyfriendlyruler':'Ruler 屏幕尺'}
OBS=['真实信息流，新闻标题与图文卡片可见','水面、赛艇、赛道及触控按钮可见','9×9 数独棋盘与启动控件','科学计算器键盘与运算面板','08:30 / 09:00 闹钟列表','双向棋钟与双方计时控件','常用计时器列表与时长','着色器代码编辑界面','骰子点数及参数设置面板','文件、URL 与播放器入口','带商品条目的购物清单','日历周视图与时间网格','本地目录与文件操作入口','四区域生命值计分面板','电压、线径与长度参数表单','带厘米刻度的屏幕尺']
for k,o in zip(SELECTED,OBS):BY[k]['selected_observation']=o

def txt(s,x,y,w,h,string,size=18,bold=False,color=FG):
 t=s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h));tf=t.text_frame;tf.word_wrap=True
 tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
 for i,line in enumerate(string.split('\n')):
  p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.space_after=Pt(6)
  run=p.add_run();run.text=line;f=run.font;f.name=FONT;f.size=Pt(size);f.bold=bold;f.color.rgb=RGBColor.from_string(color)
 return t

def rect(s,x,y,w,h,c):
 a=s.shapes.add_shape(1,Inches(x),Inches(y),Inches(w),Inches(h));a.fill.solid();a.fill.fore_color.rgb=RGBColor.from_string(c);a.line.fill.background();return a

def slide(prs,label):
 s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(BG)
 rect(s,.55,.54,.42,.045,ACCENT);txt(s,1.08,.40,10,.35,label,11,color=MUTED)
 txt(s,.6,7.12,11.7,.23,'WESTLAKE  /  Android APK on OpenHarmony  /  历史实测画面',9,color=MUTED)
 txt(s,12.1,7.10,.65,.25,f'{len(prs.slides):02}',10,color=MUTED)
 return s

def picture(s,r,x,y,w,h):
 p=OUT/r['image'];iw,ih=Image.open(p).size;scale=min(w/iw,h/ih);pw,ph=iw*scale,ih*scale
 pic=s.shapes.add_picture(str(p),Inches(x+(w-pw)/2),Inches(y+(h-ph)/2),width=Inches(pw),height=Inches(ph))
 pic.name='evidence:'+r['key'];return pic

def cover(prs,full=False):
 s=slide(prs,'APPLICATION SHOWCASE  /  2026.10.19')
 txt(s,.7,1.12,12,1.7,'Android 应用\n在 OpenHarmony 上运行',40,True)
 txt(s,.74,3.13,11.8,.6,'全量分类图册' if full else '真实画面 · 精选演示',26,color=ACCENT)
 txt(s,.75,4.15,11.5,.9,'今日头条信息流  /  BoatAttack 赛艇\n'+('128 个基准键分类收录 + 2 项专项证据' if full else '14 项具有实际界面内容的历史亮屏应用'),20)
 rect(s,.75,5.55,11.8,.018,'364559')
 txt(s,.75,5.83,11.8,.8,'基准：115 项仅启动亮屏 + 13 项排除；两项专项另计。\n应用用途与实测范围分别列示，启动亮屏不等于完整功能可用。',16,color=MUTED)

def appslide(prs,r):
 special=r['scope']=='special-extra';land=r['width']>r['height']; s=slide(prs,('专项演示' if special else '历史启动亮屏')+'  /  '+r['category'])
 name=ALIASES.get(r['key'],r['name']); left=4.0 if land else 6.6
 txt(s,.7,1.15,left,1.1,name,34 if land else 38,True)
 txt(s,.74,2.42,left,1.2,r['purpose'].rstrip('。'),23 if land else 26)
 txt(s,.74,4.1,left,.35,'画面所见',12,True,ACCENT)
 txt(s,.74,4.5,left,.8,r.get('selected_observation','历史启动界面'),18)
 txt(s,.74,5.64,left,1.1,r['verified_scope'] if special else '仅验证启动界面呈现\n未验证该应用的完整功能',13,color=MUTED)
 if land:picture(s,r,4.95,1.05,7.75,5.65)
 else:picture(s,r,7.5,.84,4.8,5.9)
 txt(s,8.0 if not land else 5.0,6.83,4.8 if not land else 7.7,.25,'实测截图 · '+r['date']+' · 原比例完整展示',9,color=MUTED)

def curated():
 p=Presentation();p.slide_width=Inches(40/3);p.slide_height=Inches(7.5);cover(p)
 for k in SELECTED:appslide(p,BY[k])
 path=OUT/'Westlake-精选演示-17页.pptx';p.save(path)
 (OUT/'selected.json').write_text(json.dumps({'keys':SELECTED,'slides':17,'welcome_pages':0},ensure_ascii=False,indent=2))
 print('READY',path)

def categorized():
 from collections import defaultdict
 p=Presentation();p.slide_width=Inches(40/3);p.slide_height=Inches(7.5);cover(p,True)
 for k in SELECTED[:2]:appslide(p,BY[k])
 cats=defaultdict(list)
 for r in ROWS[:128]:
  if r['status']!='excluded':cats[r['category']].append(r)
 for cat,items in cats.items():
  for n in range(0,len(items),3):
   s=slide(p,'分类图册 / '+cat+' / 仅启动亮屏')
   for i,r in enumerate(items[n:n+3]):
    x=.65+i*4.23;name=ALIASES.get(r['key'],r['name'])
    txt(s,x,.95,3.9,.8,name,21 if len(name)<24 else 16,True)
    txt(s,x,1.77,3.9,.72,r['purpose'],13)
    picture(s,r,x,2.55,3.8,3.8)
    txt(s,x,6.46,3.9,.42,'启动证据 · '+r['date']+'\n'+r['key'],8,color=MUTED)
 exc=[r for r in ROWS if r['status']=='excluded']
 reasons=['灰色窗口，无可识别应用内容','仅 Logo 闪屏，无地图内容','系统桌面，非应用内容','白色预览，无有效相机画面','系统桌面，非应用内容','加载界面，无游戏内容','仅 Logo 闪屏，无菜单或比赛','黑底标题，无骰子内容','界面不完整，无实质内容','白色窗口，无终端提示符','系统桌面，非应用内容','数据库更新中，无收件箱界面','数据库更新中，无收件箱界面']
 # Reasons derive from canonical exclusion list, keyed to preserve semantics.
 source=json.loads((HERE/'evidence/source-demo-list.json').read_text())
 reasonmap={r['key']:why for r,why in zip(source['excluded_keys_with_reasons'],reasons)}
 for n in range(0,len(exc),3):
  s=slide(p,'附录 / 排除项 / 不计入启动演示')
  for i,r in enumerate(exc[n:n+3]):
   x=.65+i*4.23;txt(s,x,.95,3.9,.65,r['name'],20,True)
   txt(s,x,1.65,3.9,.6,r['purpose'],12)
   picture(s,r,x,2.35,3.8,3.7)
   txt(s,x,6.15,3.9,.65,reasonmap[r['key']],12,color='F2B399')
 path=OUT/'Westlake-全量分类-128加2.pptx';p.save(path);print('CATEGORY',len(p.slides),path)
if __name__=='__main__':
 if '--full' in sys.argv:categorized()
 else:curated()
