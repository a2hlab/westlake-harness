"""Exclusive work categories for midpoint-weighted stack samples."""
import pathlib,json,collections,sys
r=pathlib.Path(sys.argv[1]);profiles=json.loads((r/'profiles.json').read_text())
rules=[('SourcePackageRegistry.contains (certificate verification lock)','adapter.packagemanager.SourcePackageRegistry.contains'),('LuckyDogSDKApiManager.initWithCallBack','com.bytedance.ug.sdk.luckydog.api.manager.LuckyDogSDKApiManager.initWithCallBack'),('VanGoghServiceImpl.init (Downloader/Mannor)','com.bytedance.news.ad.impl.VanGoghServiceImpl.init'),('SplashAdManagerHolder.initSplashAdSdk','com.ss.android.splashad.splash.SplashAdManagerHolder.initSplashAdSdk'),('ArticleApplication.npthCallInit','com.ss.android.article.news.ArticleApplication.npthCallInit'),('TranscodeConfigUtil.checkScriptConfig (lazy lock)','com.bytedance.android.xbrowser.transcode.main.transcode.TranscodeConfigUtil.checkScriptConfig'),('ContentSituationServiceImpl.uploadAppList','com.bytedance.news.ug_daoliang.content.ContentSituationServiceImpl.uploadAppList'),('EmojiCompat.load','androidx.emoji2.text.EmojiCompat.load'),('ResourcesManager.applyConfigurationToResources','android.app.ResourcesManager.applyConfigurationToResources'),('ViewRootImpl.performTraversals','android.view.ViewRootImpl.performTraversals')]
for p in profiles:
 totals=collections.defaultdict(lambda:{'estimated_ms':0,'hits':0,'lines':[],'leaf_methods':[]})
 for s in p['samples']:
  key=next((label for label,needle in rules if any(needle+'(' in f for f in s['frames'])),s['top_method'])
  t=totals[key];t['estimated_ms']+=s['estimated_occupancy_ms'];t['hits']+=1;t['lines'].append(s['line'])
  if s['top_method'] not in t['leaf_methods']:t['leaf_methods'].append(s['top_method'])
 p['work_groups']=[{'work':k,**v} for k,v in sorted(totals.items(),key=lambda x:-x[1]['estimated_ms'])]
 print(p['run'])
 for w in p['work_groups'][:7]:print(w)
(r/'work-groups.json').write_text(json.dumps(profiles,indent=2,ensure_ascii=False)+'\n')
