.class public final Ladapter/activity/J10eWebView;
.super Ljava/lang/Object;
.source "J10eWebView.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Ladapter/activity/J10eWebView$WlCookieManager;,
        Ladapter/activity/J10eWebView$ZeroH;,
        Ladapter/activity/J10eWebView$DelegateForward;,
        Ladapter/activity/J10eWebView$ProviderInstance;,
        Ladapter/activity/J10eWebView$ProviderEnrich;
    }
.end annotation


# static fields
.field private static volatile sCookie:Landroid/webkit/CookieManager;

.field private static volatile sLoggedCookie:Z

.field private static volatile sLoggedDelegate:Z


# direct methods
.method static constructor <clinit>()V
    .registers 1

    .line 66
    const/4 v0, 0x0

    sput-boolean v0, Ladapter/activity/J10eWebView;->sLoggedDelegate:Z

    .line 67
    sput-boolean v0, Ladapter/activity/J10eWebView;->sLoggedCookie:Z

    return-void
.end method

.method private constructor <init>()V
    .registers 1

    .line 64
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method static synthetic access$100()Landroid/webkit/CookieManager;
    .registers 1

    .line 63
    sget-object v0, Ladapter/activity/J10eWebView;->sCookie:Landroid/webkit/CookieManager;

    return-object v0
.end method

.method static synthetic access$102(Landroid/webkit/CookieManager;)Landroid/webkit/CookieManager;
    .registers 1

    .line 63
    sput-object p0, Ladapter/activity/J10eWebView;->sCookie:Landroid/webkit/CookieManager;

    return-object p0
.end method

.method static synthetic access$200()Z
    .registers 1

    .line 63
    sget-boolean v0, Ladapter/activity/J10eWebView;->sLoggedCookie:Z

    return v0
.end method

.method static synthetic access$202(Z)Z
    .registers 1

    .line 63
    sput-boolean p0, Ladapter/activity/J10eWebView;->sLoggedCookie:Z

    return p0
.end method

.method static synthetic access$300()Z
    .registers 1

    .line 63
    sget-boolean v0, Ladapter/activity/J10eWebView;->sLoggedDelegate:Z

    return v0
.end method

.method static synthetic access$302(Z)Z
    .registers 1

    .line 63
    sput-boolean p0, Ladapter/activity/J10eWebView;->sLoggedDelegate:Z

    return p0
.end method

.method public static install()V
    .registers 6

    .line 75
    :try_start_0
    const-string v0, "android.webkit.WebViewFactory"

    invoke-static {v0}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v0

    .line 76
    const-string v1, "sProviderInstance"

    invoke-virtual {v0, v1}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v0

    .line 77
    const/4 v1, 0x1

    invoke-virtual {v0, v1}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    .line 78
    const/4 v2, 0x0

    invoke-virtual {v0, v2}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v3

    .line 79
    if-eqz v3, :cond_2a

    invoke-virtual {v3}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v4

    invoke-static {v4}, Ljava/lang/reflect/Proxy;->isProxyClass(Ljava/lang/Class;)Z

    move-result v4

    if-eqz v4, :cond_2a

    .line 80
    invoke-static {v3}, Ljava/lang/reflect/Proxy;->getInvocationHandler(Ljava/lang/Object;)Ljava/lang/reflect/InvocationHandler;

    move-result-object v3

    instance-of v3, v3, Ladapter/activity/J10eWebView$ProviderEnrich;

    if-eqz v3, :cond_2a

    .line 81
    return-void

    .line 83
    :cond_2a
    const-string v3, "android.webkit.WebViewFactoryProvider"

    invoke-static {v3}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v3

    .line 84
    invoke-virtual {v3}, Ljava/lang/Class;->getClassLoader()Ljava/lang/ClassLoader;

    move-result-object v4

    new-array v1, v1, [Ljava/lang/Class;

    const/4 v5, 0x0

    aput-object v3, v1, v5

    new-instance v3, Ladapter/activity/J10eWebView$ProviderEnrich;

    invoke-direct {v3, v2}, Ladapter/activity/J10eWebView$ProviderEnrich;-><init>(Ladapter/activity/J10eWebView$1;)V

    invoke-static {v4, v1, v3}, Ljava/lang/reflect/Proxy;->newProxyInstance(Ljava/lang/ClassLoader;[Ljava/lang/Class;Ljava/lang/reflect/InvocationHandler;)Ljava/lang/Object;

    move-result-object v1

    .line 86
    invoke-virtual {v0, v2, v1}, Ljava/lang/reflect/Field;->set(Ljava/lang/Object;Ljava/lang/Object;)V

    .line 87
    sget-object v0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v1, "[J10e-WEBVIEW] enriched WebViewFactoryProvider seeded (forwarding ViewDelegate + concrete CookieManager/WebStorage/Geolocation)"

    invoke-virtual {v0, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_4c
    .catchall {:try_start_0 .. :try_end_4c} :catchall_4d

    .line 91
    goto :goto_66

    .line 89
    :catchall_4d
    move-exception v0

    .line 90
    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "[J10e-WEBVIEW] install failed: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v1, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 92
    :goto_66
    return-void
.end method

.method static zero(Ljava/lang/Class;)Ljava/lang/Object;
    .registers 5
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "(",
            "Ljava/lang/Class<",
            "*>;)",
            "Ljava/lang/Object;"
        }
    .end annotation

    .line 168
    sget-object v0, Ljava/lang/Boolean;->TYPE:Ljava/lang/Class;

    if-ne p0, v0, :cond_7

    sget-object p0, Ljava/lang/Boolean;->FALSE:Ljava/lang/Boolean;

    return-object p0

    .line 169
    :cond_7
    sget-object v0, Ljava/lang/Integer;->TYPE:Ljava/lang/Class;

    const/4 v1, 0x0

    if-ne p0, v0, :cond_11

    invoke-static {v1}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object p0

    return-object p0

    .line 170
    :cond_11
    sget-object v0, Ljava/lang/Long;->TYPE:Ljava/lang/Class;

    if-ne p0, v0, :cond_1c

    const-wide/16 v0, 0x0

    invoke-static {v0, v1}, Ljava/lang/Long;->valueOf(J)Ljava/lang/Long;

    move-result-object p0

    return-object p0

    .line 171
    :cond_1c
    sget-object v0, Ljava/lang/Void;->TYPE:Ljava/lang/Class;

    const/4 v2, 0x0

    if-ne p0, v0, :cond_22

    return-object v2

    .line 172
    :cond_22
    invoke-virtual {p0}, Ljava/lang/Class;->isArray()Z

    move-result v0

    if-eqz v0, :cond_31

    invoke-virtual {p0}, Ljava/lang/Class;->getComponentType()Ljava/lang/Class;

    move-result-object p0

    invoke-static {p0, v1}, Ljava/lang/reflect/Array;->newInstance(Ljava/lang/Class;I)Ljava/lang/Object;

    move-result-object p0

    return-object p0

    .line 173
    :cond_31
    invoke-virtual {p0}, Ljava/lang/Class;->isInterface()Z

    move-result v0

    if-eqz v0, :cond_4c

    .line 174
    :try_start_37
    invoke-virtual {p0}, Ljava/lang/Class;->getClassLoader()Ljava/lang/ClassLoader;

    move-result-object v0

    const/4 v3, 0x1

    new-array v3, v3, [Ljava/lang/Class;

    aput-object p0, v3, v1

    new-instance p0, Ladapter/activity/J10eWebView$ZeroH;

    invoke-direct {p0, v2}, Ladapter/activity/J10eWebView$ZeroH;-><init>(Ladapter/activity/J10eWebView$1;)V

    invoke-static {v0, v3, p0}, Ljava/lang/reflect/Proxy;->newProxyInstance(Ljava/lang/ClassLoader;[Ljava/lang/Class;Ljava/lang/reflect/InvocationHandler;)Ljava/lang/Object;

    move-result-object p0
    :try_end_49
    .catchall {:try_start_37 .. :try_end_49} :catchall_4a

    return-object p0

    .line 175
    :catchall_4a
    move-exception p0

    return-object v2

    .line 177
    :cond_4c
    return-object v2
.end method
