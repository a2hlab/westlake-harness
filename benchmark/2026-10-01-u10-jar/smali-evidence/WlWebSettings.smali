.class final Ladapter/activity/J10fWebSettings$WlWebSettings;
.super Landroid/webkit/WebSettings;
.source "J10fWebSettings.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Ladapter/activity/J10fWebSettings;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x18
    name = "WlWebSettings"
.end annotation


# direct methods
.method constructor <init>()V
    .registers 1

    .line 23
    invoke-direct {p0}, Landroid/webkit/WebSettings;-><init>()V

    return-void
.end method


# virtual methods
.method public enableSmoothTransition()Z
    .registers 2

    .line 41
    const/4 v0, 0x0

    return v0
.end method

.method public getAcceptThirdPartyCookies()Z
    .registers 2

    .line 51
    const/4 v0, 0x0

    return v0
.end method

.method public getAllowContentAccess()Z
    .registers 2

    .line 37
    const/4 v0, 0x0

    return v0
.end method

.method public getAllowFileAccess()Z
    .registers 2

    .line 35
    const/4 v0, 0x0

    return v0
.end method

.method public getAllowFileAccessFromFileURLs()Z
    .registers 2

    .line 105
    const/4 v0, 0x0

    return v0
.end method

.method public getAllowUniversalAccessFromFileURLs()Z
    .registers 2

    .line 104
    const/4 v0, 0x0

    return v0
.end method

.method public getBlockNetworkImage()Z
    .registers 2

    .line 87
    const/4 v0, 0x0

    return v0
.end method

.method public getBlockNetworkLoads()Z
    .registers 2

    .line 89
    const/4 v0, 0x0

    return v0
.end method

.method public getBuiltInZoomControls()Z
    .registers 2

    .line 31
    const/4 v0, 0x0

    return v0
.end method

.method public getCacheMode()I
    .registers 2

    .line 117
    const/4 v0, 0x0

    return v0
.end method

.method public getCursiveFontFamily()Ljava/lang/String;
    .registers 2

    .line 73
    const-string v0, "cursive"

    return-object v0
.end method

.method public getDatabaseEnabled()Z
    .registers 2

    .line 101
    const/4 v0, 0x0

    return v0
.end method

.method public getDatabasePath()Ljava/lang/String;
    .registers 2

    .line 100
    const-string v0, ""

    return-object v0
.end method

.method public getDefaultFixedFontSize()I
    .registers 2

    .line 83
    const/4 v0, 0x0

    return v0
.end method

.method public getDefaultFontSize()I
    .registers 2

    .line 81
    const/4 v0, 0x0

    return v0
.end method

.method public getDefaultTextEncodingName()Ljava/lang/String;
    .registers 2

    .line 111
    const-string v0, "UTF-8"

    return-object v0
.end method

.method public getDefaultZoom()Landroid/webkit/WebSettings$ZoomDensity;
    .registers 2

    .line 53
    sget-object v0, Landroid/webkit/WebSettings$ZoomDensity;->MEDIUM:Landroid/webkit/WebSettings$ZoomDensity;

    return-object v0
.end method

.method public getDisabledActionModeMenuItems()I
    .registers 2

    .line 127
    const/4 v0, 0x0

    return v0
.end method

.method public getDisplayZoomControls()Z
    .registers 2

    .line 33
    const/4 v0, 0x0

    return v0
.end method

.method public getDomStorageEnabled()Z
    .registers 2

    .line 99
    const/4 v0, 0x0

    return v0
.end method

.method public getFantasyFontFamily()Ljava/lang/String;
    .registers 2

    .line 75
    const-string v0, "fantasy"

    return-object v0
.end method

.method public getFixedFontFamily()Ljava/lang/String;
    .registers 2

    .line 67
    const-string v0, "monospace"

    return-object v0
.end method

.method public getJavaScriptCanOpenWindowsAutomatically()Z
    .registers 2

    .line 109
    const/4 v0, 0x0

    return v0
.end method

.method public getJavaScriptEnabled()Z
    .registers 2

    .line 103
    const/4 v0, 0x0

    return v0
.end method

.method public getLayoutAlgorithm()Landroid/webkit/WebSettings$LayoutAlgorithm;
    .registers 2

    .line 63
    sget-object v0, Landroid/webkit/WebSettings$LayoutAlgorithm;->NARROW_COLUMNS:Landroid/webkit/WebSettings$LayoutAlgorithm;

    return-object v0
.end method

.method public getLightTouchEnabled()Z
    .registers 2

    .line 55
    const/4 v0, 0x0

    return v0
.end method

.method public getLoadWithOverviewMode()Z
    .registers 2

    .line 39
    const/4 v0, 0x0

    return v0
.end method

.method public getLoadsImagesAutomatically()Z
    .registers 2

    .line 85
    const/4 v0, 0x0

    return v0
.end method

.method public getMediaPlaybackRequiresUserGesture()Z
    .registers 2

    .line 29
    const/4 v0, 0x0

    return v0
.end method

.method public getMinimumFontSize()I
    .registers 2

    .line 77
    const/4 v0, 0x0

    return v0
.end method

.method public getMinimumLogicalFontSize()I
    .registers 2

    .line 79
    const/4 v0, 0x0

    return v0
.end method

.method public getMixedContentMode()I
    .registers 2

    .line 119
    const/4 v0, 0x0

    return v0
.end method

.method public getNavDump()Z
    .registers 2

    .line 25
    const/4 v0, 0x0

    return v0
.end method

.method public getOffscreenPreRaster()Z
    .registers 2

    .line 123
    const/4 v0, 0x0

    return v0
.end method

.method public getPluginState()Landroid/webkit/WebSettings$PluginState;
    .registers 2

    .line 107
    sget-object v0, Landroid/webkit/WebSettings$PluginState;->OFF:Landroid/webkit/WebSettings$PluginState;

    return-object v0
.end method

.method public getPluginsEnabled()Z
    .registers 2

    .line 106
    const/4 v0, 0x0

    return v0
.end method

.method public getSafeBrowsingEnabled()Z
    .registers 2

    .line 125
    const/4 v0, 0x0

    return v0
.end method

.method public getSansSerifFontFamily()Ljava/lang/String;
    .registers 2

    .line 69
    const-string v0, "sans-serif"

    return-object v0
.end method

.method public getSaveFormData()Z
    .registers 2

    .line 45
    const/4 v0, 0x0

    return v0
.end method

.method public getSavePassword()Z
    .registers 2

    .line 47
    const/4 v0, 0x0

    return v0
.end method

.method public getSerifFontFamily()Ljava/lang/String;
    .registers 2

    .line 71
    const-string v0, "serif"

    return-object v0
.end method

.method public getStandardFontFamily()Ljava/lang/String;
    .registers 2

    .line 65
    const-string v0, "sans-serif"

    return-object v0
.end method

.method public getTextZoom()I
    .registers 2

    .line 49
    const/4 v0, 0x0

    return v0
.end method

.method public getUseWebViewBackgroundForOverscrollBackground()Z
    .registers 2

    .line 43
    const/4 v0, 0x0

    return v0
.end method

.method public getUseWideViewPort()Z
    .registers 2

    .line 59
    const/4 v0, 0x0

    return v0
.end method

.method public getUserAgent()I
    .registers 2

    .line 57
    const/4 v0, 0x0

    return v0
.end method

.method public getUserAgentString()Ljava/lang/String;
    .registers 2

    .line 113
    const-string v0, "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/125.0.0.0 Mobile Safari/537.36"

    return-object v0
.end method

.method public getVideoOverlayForEmbeddedEncryptedVideoEnabled()Z
    .registers 2

    .line 121
    const/4 v0, 0x0

    return v0
.end method

.method public setAcceptThirdPartyCookies(Z)V
    .registers 2

    .line 50
    return-void
.end method

.method public setAllowContentAccess(Z)V
    .registers 2

    .line 36
    return-void
.end method

.method public setAllowFileAccess(Z)V
    .registers 2

    .line 34
    return-void
.end method

.method public setAllowFileAccessFromFileURLs(Z)V
    .registers 2

    .line 92
    return-void
.end method

.method public setAllowUniversalAccessFromFileURLs(Z)V
    .registers 2

    .line 91
    return-void
.end method

.method public setBlockNetworkImage(Z)V
    .registers 2

    .line 86
    return-void
.end method

.method public setBlockNetworkLoads(Z)V
    .registers 2

    .line 88
    return-void
.end method

.method public setBuiltInZoomControls(Z)V
    .registers 2

    .line 30
    return-void
.end method

.method public setCacheMode(I)V
    .registers 2

    .line 116
    return-void
.end method

.method public setCursiveFontFamily(Ljava/lang/String;)V
    .registers 2

    .line 72
    return-void
.end method

.method public setDatabaseEnabled(Z)V
    .registers 2

    .line 97
    return-void
.end method

.method public setDatabasePath(Ljava/lang/String;)V
    .registers 2

    .line 95
    return-void
.end method

.method public setDefaultFixedFontSize(I)V
    .registers 2

    .line 82
    return-void
.end method

.method public setDefaultFontSize(I)V
    .registers 2

    .line 80
    return-void
.end method

.method public setDefaultTextEncodingName(Ljava/lang/String;)V
    .registers 2

    .line 110
    return-void
.end method

.method public setDefaultZoom(Landroid/webkit/WebSettings$ZoomDensity;)V
    .registers 2

    .line 52
    return-void
.end method

.method public setDisabledActionModeMenuItems(I)V
    .registers 2

    .line 126
    return-void
.end method

.method public setDisplayZoomControls(Z)V
    .registers 2

    .line 32
    return-void
.end method

.method public setDomStorageEnabled(Z)V
    .registers 2

    .line 98
    return-void
.end method

.method public setEnableSmoothTransition(Z)V
    .registers 2

    .line 40
    return-void
.end method

.method public setFantasyFontFamily(Ljava/lang/String;)V
    .registers 2

    .line 74
    return-void
.end method

.method public setFixedFontFamily(Ljava/lang/String;)V
    .registers 2

    .line 66
    return-void
.end method

.method public setGeolocationDatabasePath(Ljava/lang/String;)V
    .registers 2

    .line 96
    return-void
.end method

.method public setGeolocationEnabled(Z)V
    .registers 2

    .line 102
    return-void
.end method

.method public setJavaScriptCanOpenWindowsAutomatically(Z)V
    .registers 2

    .line 108
    return-void
.end method

.method public setJavaScriptEnabled(Z)V
    .registers 2

    .line 90
    return-void
.end method

.method public setLayoutAlgorithm(Landroid/webkit/WebSettings$LayoutAlgorithm;)V
    .registers 2

    .line 62
    return-void
.end method

.method public setLightTouchEnabled(Z)V
    .registers 2

    .line 54
    return-void
.end method

.method public setLoadWithOverviewMode(Z)V
    .registers 2

    .line 38
    return-void
.end method

.method public setLoadsImagesAutomatically(Z)V
    .registers 2

    .line 84
    return-void
.end method

.method public setMediaPlaybackRequiresUserGesture(Z)V
    .registers 2

    .line 28
    return-void
.end method

.method public setMinimumFontSize(I)V
    .registers 2

    .line 76
    return-void
.end method

.method public setMinimumLogicalFontSize(I)V
    .registers 2

    .line 78
    return-void
.end method

.method public setMixedContentMode(I)V
    .registers 2

    .line 118
    return-void
.end method

.method public setNavDump(Z)V
    .registers 2

    .line 24
    return-void
.end method

.method public setNeedInitialFocus(Z)V
    .registers 2

    .line 114
    return-void
.end method

.method public setOffscreenPreRaster(Z)V
    .registers 2

    .line 122
    return-void
.end method

.method public setPluginState(Landroid/webkit/WebSettings$PluginState;)V
    .registers 2

    .line 94
    return-void
.end method

.method public setPluginsEnabled(Z)V
    .registers 2

    .line 93
    return-void
.end method

.method public setRenderPriority(Landroid/webkit/WebSettings$RenderPriority;)V
    .registers 2

    .line 115
    return-void
.end method

.method public setSafeBrowsingEnabled(Z)V
    .registers 2

    .line 124
    return-void
.end method

.method public setSansSerifFontFamily(Ljava/lang/String;)V
    .registers 2

    .line 68
    return-void
.end method

.method public setSaveFormData(Z)V
    .registers 2

    .line 44
    return-void
.end method

.method public setSavePassword(Z)V
    .registers 2

    .line 46
    return-void
.end method

.method public setSerifFontFamily(Ljava/lang/String;)V
    .registers 2

    .line 70
    return-void
.end method

.method public setStandardFontFamily(Ljava/lang/String;)V
    .registers 2

    .line 64
    return-void
.end method

.method public setSupportMultipleWindows(Z)V
    .registers 2

    .line 60
    return-void
.end method

.method public setSupportZoom(Z)V
    .registers 2

    .line 26
    return-void
.end method

.method public setTextZoom(I)V
    .registers 2

    .line 48
    return-void
.end method

.method public setUseWebViewBackgroundForOverscrollBackground(Z)V
    .registers 2

    .line 42
    return-void
.end method

.method public setUseWideViewPort(Z)V
    .registers 2

    .line 58
    return-void
.end method

.method public setUserAgent(I)V
    .registers 2

    .line 56
    return-void
.end method

.method public setUserAgentString(Ljava/lang/String;)V
    .registers 2

    .line 112
    return-void
.end method

.method public setVideoOverlayForEmbeddedEncryptedVideoEnabled(Z)V
    .registers 2

    .line 120
    return-void
.end method

.method public supportMultipleWindows()Z
    .registers 2

    .line 61
    const/4 v0, 0x0

    return v0
.end method

.method public supportZoom()Z
    .registers 2

    .line 27
    const/4 v0, 0x0

    return v0
.end method
