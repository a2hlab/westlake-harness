.class public final Ladapter/activity/J10fWebSettings;
.super Ljava/lang/Object;
.source "J10fWebSettings.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Ladapter/activity/J10fWebSettings$WlWebSettings;
    }
.end annotation


# static fields
.field private static volatile sLogged:Z

.field private static volatile sSettings:Landroid/webkit/WebSettings;


# direct methods
.method static constructor <clinit>()V
    .registers 1

    .line 13
    const/4 v0, 0x0

    sput-boolean v0, Ladapter/activity/J10fWebSettings;->sLogged:Z

    return-void
.end method

.method private constructor <init>()V
    .registers 1

    .line 12
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static get()Landroid/webkit/WebSettings;
    .registers 2

    .line 18
    sget-object v0, Ladapter/activity/J10fWebSettings;->sSettings:Landroid/webkit/WebSettings;

    if-nez v0, :cond_b

    new-instance v0, Ladapter/activity/J10fWebSettings$WlWebSettings;

    invoke-direct {v0}, Ladapter/activity/J10fWebSettings$WlWebSettings;-><init>()V

    sput-object v0, Ladapter/activity/J10fWebSettings;->sSettings:Landroid/webkit/WebSettings;

    .line 19
    :cond_b
    sget-boolean v0, Ladapter/activity/J10fWebSettings;->sLogged:Z

    if-nez v0, :cond_19

    const/4 v0, 0x1

    sput-boolean v0, Ladapter/activity/J10fWebSettings;->sLogged:Z

    sget-object v0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v1, "[J10f-WEBVIEW] settings stub installed"

    invoke-virtual {v0, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 20
    :cond_19
    sget-object v0, Ladapter/activity/J10fWebSettings;->sSettings:Landroid/webkit/WebSettings;

    return-object v0
.end method
