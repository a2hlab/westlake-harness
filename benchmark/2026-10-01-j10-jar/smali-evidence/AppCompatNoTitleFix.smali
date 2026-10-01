.class public final Ladapter/activity/AppCompatNoTitleFix;
.super Ljava/lang/Object;
.source "AppCompatNoTitleFix.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Ladapter/activity/AppCompatNoTitleFix$Callbacks;
    }
.end annotation


# static fields
.field private static volatile sInstalled:Z


# direct methods
.method static constructor <clinit>()V
    .registers 1

    .line 37
    const/4 v0, 0x0

    sput-boolean v0, Ladapter/activity/AppCompatNoTitleFix;->sInstalled:Z

    return-void
.end method

.method private constructor <init>()V
    .registers 1

    .line 35
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method static synthetic access$100(Landroid/app/Activity;)Z
    .registers 1

    .line 34
    invoke-static {p0}, Ladapter/activity/AppCompatNoTitleFix;->isAppCompatActivity(Landroid/app/Activity;)Z

    move-result p0

    return p0
.end method

.method private static currentApplication()Landroid/app/Application;
    .registers 5

    .line 69
    const/4 v0, 0x0

    :try_start_1
    const-string v1, "android.app.ActivityThread"

    invoke-static {v1}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v1

    .line 70
    const-string v2, "currentApplication"

    const/4 v3, 0x0

    new-array v4, v3, [Ljava/lang/Class;

    invoke-virtual {v1, v2, v4}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v1

    new-array v2, v3, [Ljava/lang/Object;

    invoke-virtual {v1, v0, v2}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    .line 71
    check-cast v1, Landroid/app/Application;
    :try_end_18
    .catchall {:try_start_1 .. :try_end_18} :catchall_19

    return-object v1

    .line 72
    :catchall_19
    move-exception v1

    .line 73
    return-object v0
.end method

.method public static install()V
    .registers 1

    .line 50
    invoke-static {}, Ladapter/activity/AppCompatNoTitleFix;->currentApplication()Landroid/app/Application;

    move-result-object v0

    invoke-static {v0}, Ladapter/activity/AppCompatNoTitleFix;->install(Landroid/app/Application;)V

    .line 51
    return-void
.end method

.method public static declared-synchronized install(Landroid/app/Application;)V
    .registers 5

    const-class v0, Ladapter/activity/AppCompatNoTitleFix;

    monitor-enter v0

    .line 57
    :try_start_3
    sget-boolean v1, Ladapter/activity/AppCompatNoTitleFix;->sInstalled:Z
    :try_end_5
    .catchall {:try_start_3 .. :try_end_5} :catchall_21

    if-eqz v1, :cond_9

    monitor-exit v0

    return-void

    .line 58
    :cond_9
    if-nez p0, :cond_d

    monitor-exit v0

    return-void

    .line 59
    :cond_d
    :try_start_d
    new-instance v1, Ladapter/activity/AppCompatNoTitleFix$Callbacks;

    const/4 v2, 0x0

    invoke-direct {v1, v2}, Ladapter/activity/AppCompatNoTitleFix$Callbacks;-><init>(Ladapter/activity/AppCompatNoTitleFix$1;)V

    invoke-virtual {p0, v1}, Landroid/app/Application;->registerActivityLifecycleCallbacks(Landroid/app/Application$ActivityLifecycleCallbacks;)V

    .line 60
    const/4 p0, 0x1

    sput-boolean p0, Ladapter/activity/AppCompatNoTitleFix;->sInstalled:Z

    .line 61
    sget-object p0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v1, "[J10-NOTITLE] installed"

    invoke-virtual {p0, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_20
    .catchall {:try_start_d .. :try_end_20} :catchall_21

    .line 64
    goto :goto_3a

    .line 62
    :catchall_21
    move-exception p0

    .line 63
    :try_start_22
    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "[J10-NOTITLE] install failed: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {v1, p0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_3a
    .catchall {:try_start_22 .. :try_end_3a} :catchall_3c

    .line 65
    :goto_3a
    monitor-exit v0

    return-void

    .line 56
    :catchall_3c
    move-exception p0

    :try_start_3d
    monitor-exit v0
    :try_end_3e
    .catchall {:try_start_3d .. :try_end_3e} :catchall_3c

    throw p0
.end method

.method private static isAppCompatActivity(Landroid/app/Activity;)Z
    .registers 3

    .line 78
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object p0

    :goto_4
    if-eqz p0, :cond_26

    const-class v0, Landroid/app/Activity;

    if-eq p0, v0, :cond_26

    .line 79
    invoke-virtual {p0}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object v0

    .line 80
    const-string v1, "androidx.appcompat.app.AppCompatActivity"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-nez v1, :cond_24

    .line 81
    const-string v1, "android.support.v7.app.AppCompatActivity"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :cond_1f

    goto :goto_24

    .line 78
    :cond_1f
    invoke-virtual {p0}, Ljava/lang/Class;->getSuperclass()Ljava/lang/Class;

    move-result-object p0

    goto :goto_4

    .line 82
    :cond_24
    :goto_24
    const/4 p0, 0x1

    return p0

    .line 85
    :cond_26
    const/4 p0, 0x0

    return p0
.end method
