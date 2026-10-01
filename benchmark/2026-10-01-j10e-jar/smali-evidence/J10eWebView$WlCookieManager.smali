.class final Ladapter/activity/J10eWebView$WlCookieManager;
.super Landroid/webkit/CookieManager;
.source "J10eWebView.java"


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Ladapter/activity/J10eWebView;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x18
    name = "WlCookieManager"
.end annotation


# direct methods
.method constructor <init>()V
    .registers 1

    .line 191
    invoke-direct {p0}, Landroid/webkit/CookieManager;-><init>()V

    return-void
.end method


# virtual methods
.method public acceptCookie()Z
    .registers 2

    .line 193
    const/4 v0, 0x1

    return v0
.end method

.method public acceptThirdPartyCookies(Landroid/webkit/WebView;)Z
    .registers 2

    .line 195
    const/4 p1, 0x0

    return p1
.end method

.method public flush()V
    .registers 1

    .line 207
    return-void
.end method

.method public getCookie(Ljava/lang/String;)Ljava/lang/String;
    .registers 2

    .line 198
    const/4 p1, 0x0

    return-object p1
.end method

.method public getCookie(Ljava/lang/String;Z)Ljava/lang/String;
    .registers 3

    .line 199
    const/4 p1, 0x0

    return-object p1
.end method

.method public hasCookies()Z
    .registers 2

    .line 204
    const/4 v0, 0x0

    return v0
.end method

.method public hasCookies(Z)Z
    .registers 2

    .line 205
    const/4 p1, 0x0

    return p1
.end method

.method public removeAllCookie()V
    .registers 1

    .line 202
    return-void
.end method

.method public removeAllCookies(Landroid/webkit/ValueCallback;)V
    .registers 2
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Landroid/webkit/ValueCallback<",
            "Ljava/lang/Boolean;",
            ">;)V"
        }
    .end annotation

    .line 203
    return-void
.end method

.method public removeExpiredCookie()V
    .registers 1

    .line 206
    return-void
.end method

.method public removeSessionCookie()V
    .registers 1

    .line 200
    return-void
.end method

.method public removeSessionCookies(Landroid/webkit/ValueCallback;)V
    .registers 2
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Landroid/webkit/ValueCallback<",
            "Ljava/lang/Boolean;",
            ">;)V"
        }
    .end annotation

    .line 201
    return-void
.end method

.method public setAcceptCookie(Z)V
    .registers 2

    .line 192
    return-void
.end method

.method public setAcceptThirdPartyCookies(Landroid/webkit/WebView;Z)V
    .registers 3

    .line 194
    return-void
.end method

.method public setCookie(Ljava/lang/String;Ljava/lang/String;)V
    .registers 3

    .line 196
    return-void
.end method

.method public setCookie(Ljava/lang/String;Ljava/lang/String;Landroid/webkit/ValueCallback;)V
    .registers 4
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Ljava/lang/String;",
            "Ljava/lang/String;",
            "Landroid/webkit/ValueCallback<",
            "Ljava/lang/Boolean;",
            ">;)V"
        }
    .end annotation

    .line 197
    return-void
.end method
