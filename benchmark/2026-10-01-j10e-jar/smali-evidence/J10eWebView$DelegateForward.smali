.class final Ladapter/activity/J10eWebView$DelegateForward;
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
    name = "DelegateForward"
.end annotation


# instance fields
.field private final privateAccess:Ljava/lang/Object;


# direct methods
.method constructor <init>(Ljava/lang/Object;)V
    .registers 2

    .line 141
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Ladapter/activity/J10eWebView$DelegateForward;->privateAccess:Ljava/lang/Object;

    return-void
.end method


# virtual methods
.method public invoke(Ljava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;)Ljava/lang/Object;
    .registers 8

    .line 143
    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getName()Ljava/lang/String;

    move-result-object v0

    .line 144
    const-string v1, "toString"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :cond_f

    const-string p1, "WlViewDelegate"

    return-object p1

    .line 145
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

    .line 146
    :cond_20
    const-string v1, "equals"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    const/4 v2, 0x1

    if-eqz v1, :cond_3a

    const/4 p2, 0x0

    if-eqz p3, :cond_34

    array-length v0, p3

    if-ne v0, v2, :cond_34

    aget-object p3, p3, p2

    if-ne p3, p1, :cond_34

    goto :goto_35

    :cond_34
    move v2, p2

    :goto_35
    invoke-static {v2}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object p1

    return-object p1

    .line 147
    :cond_3a
    iget-object p1, p0, Ladapter/activity/J10eWebView$DelegateForward;->privateAccess:Ljava/lang/Object;

    if-eqz p1, :cond_82

    .line 149
    :try_start_3e
    iget-object p1, p0, Ladapter/activity/J10eWebView$DelegateForward;->privateAccess:Ljava/lang/Object;

    invoke-virtual {p1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object p1

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "super_"

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getParameterTypes()[Ljava/lang/Class;

    move-result-object v3

    invoke-virtual {p1, v1, v3}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object p1

    .line 150
    iget-object v1, p0, Ladapter/activity/J10eWebView$DelegateForward;->privateAccess:Ljava/lang/Object;

    invoke-virtual {p1, v1, p3}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p1

    .line 151
    const-string p3, "setLayoutParams"

    invoke-virtual {p3, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p3

    if-eqz p3, :cond_7d

    # getter for: Ladapter/activity/J10eWebView;->sLoggedDelegate:Z
    invoke-static {}, Ladapter/activity/J10eWebView;->access$300()Z

    move-result p3

    if-nez p3, :cond_7d

    .line 152
    # setter for: Ladapter/activity/J10eWebView;->sLoggedDelegate:Z
    invoke-static {v2}, Ladapter/activity/J10eWebView;->access$302(Z)Z

    .line 153
    sget-object p3, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v0, "[J10e-WEBVIEW] delegate forwards setLayoutParams"

    invoke-virtual {p3, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_7d
    .catch Ljava/lang/NoSuchMethodException; {:try_start_3e .. :try_end_7d} :catch_80
    .catchall {:try_start_3e .. :try_end_7d} :catchall_7e

    .line 155
    :cond_7d
    return-object p1

    .line 158
    :catchall_7e
    move-exception p1

    goto :goto_82

    .line 156
    :catch_80
    move-exception p1

    .line 160
    nop

    .line 162
    :cond_82
    :goto_82
    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getReturnType()Ljava/lang/Class;

    move-result-object p1

    invoke-static {p1}, Ladapter/activity/J10eWebView;->zero(Ljava/lang/Class;)Ljava/lang/Object;

    move-result-object p1

    return-object p1
.end method
