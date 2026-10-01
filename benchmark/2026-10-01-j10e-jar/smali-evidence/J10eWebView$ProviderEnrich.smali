.class final Ladapter/activity/J10eWebView$ProviderEnrich;
.super Ljava/lang/Object;
.source "J10eWebView.java"

# interfaces
.implements Ljava/lang/reflect/InvocationHandler;


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Ladapter/activity/J10eWebView;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x1a
    name = "ProviderEnrich"
.end annotation


# direct methods
.method private constructor <init>()V
    .registers 1

    .line 95
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method synthetic constructor <init>(Ladapter/activity/J10eWebView$1;)V
    .registers 2

    .line 95
    invoke-direct {p0}, Ladapter/activity/J10eWebView$ProviderEnrich;-><init>()V

    return-void
.end method


# virtual methods
.method public invoke(Ljava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;)Ljava/lang/Object;
    .registers 8

    .line 97
    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getName()Ljava/lang/String;

    move-result-object v0

    .line 98
    const-string v1, "toString"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :cond_f

    const-string p1, "WlEnrichedWebViewFactoryProvider"

    return-object p1

    .line 99
    :cond_f
    const-string v1, "hashCode"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :cond_20

    invoke-static {p1}, Ljava/lang/System;->identityHashCode(Ljava/lang/Object;)I

    move-result p1

    invoke-static {p1}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object p1

    return-object p1

    .line 100
    :cond_20
    const-string v1, "equals"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    const/4 v2, 0x0

    const/4 v3, 0x1

    if-eqz v1, :cond_39

    if-eqz p3, :cond_34

    array-length p2, p3

    if-ne p2, v3, :cond_34

    aget-object p2, p3, v2

    if-ne p2, p1, :cond_34

    move v2, v3

    :cond_34
    invoke-static {v2}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object p1

    return-object p1

    .line 101
    :cond_39
    const-string p1, "createWebView"

    invoke-virtual {p1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p1

    if-eqz p1, :cond_61

    .line 102
    if-eqz p3, :cond_4a

    array-length p1, p3

    const/4 v0, 0x2

    if-lt p1, v0, :cond_4a

    aget-object p1, p3, v3

    goto :goto_4b

    :cond_4a
    const/4 p1, 0x0

    .line 103
    :goto_4b
    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getReturnType()Ljava/lang/Class;

    move-result-object p2

    .line 104
    invoke-virtual {p2}, Ljava/lang/Class;->getClassLoader()Ljava/lang/ClassLoader;

    move-result-object p3

    new-array v0, v3, [Ljava/lang/Class;

    aput-object p2, v0, v2

    new-instance p2, Ladapter/activity/J10eWebView$ProviderInstance;

    invoke-direct {p2, p1}, Ladapter/activity/J10eWebView$ProviderInstance;-><init>(Ljava/lang/Object;)V

    invoke-static {p3, v0, p2}, Ljava/lang/reflect/Proxy;->newProxyInstance(Ljava/lang/ClassLoader;[Ljava/lang/Class;Ljava/lang/reflect/InvocationHandler;)Ljava/lang/Object;

    move-result-object p1

    return-object p1

    .line 107
    :cond_61
    const-string p1, "getCookieManager"

    invoke-virtual {p1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p1

    if-eqz p1, :cond_8c

    .line 108
    # getter for: Ladapter/activity/J10eWebView;->sCookie:Landroid/webkit/CookieManager;
    invoke-static {}, Ladapter/activity/J10eWebView;->access$100()Landroid/webkit/CookieManager;

    move-result-object p1

    if-nez p1, :cond_77

    new-instance p1, Ladapter/activity/J10eWebView$WlCookieManager;

    invoke-direct {p1}, Ladapter/activity/J10eWebView$WlCookieManager;-><init>()V

    # setter for: Ladapter/activity/J10eWebView;->sCookie:Landroid/webkit/CookieManager;
    invoke-static {p1}, Ladapter/activity/J10eWebView;->access$102(Landroid/webkit/CookieManager;)Landroid/webkit/CookieManager;

    .line 109
    :cond_77
    # getter for: Ladapter/activity/J10eWebView;->sLoggedCookie:Z
    invoke-static {}, Ladapter/activity/J10eWebView;->access$200()Z

    move-result p1

    if-nez p1, :cond_87

    # setter for: Ladapter/activity/J10eWebView;->sLoggedCookie:Z
    invoke-static {v3}, Ladapter/activity/J10eWebView;->access$202(Z)Z

    .line 110
    sget-object p1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string p2, "[J10e-WEBVIEW] CookieManager stub installed"

    invoke-virtual {p1, p2}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 111
    :cond_87
    # getter for: Ladapter/activity/J10eWebView;->sCookie:Landroid/webkit/CookieManager;
    invoke-static {}, Ladapter/activity/J10eWebView;->access$100()Landroid/webkit/CookieManager;

    move-result-object p1

    return-object p1

    .line 116
    :cond_8c
    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getReturnType()Ljava/lang/Class;

    move-result-object p1

    invoke-static {p1}, Ladapter/activity/J10eWebView;->zero(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p1

    return-object p1
.end method
