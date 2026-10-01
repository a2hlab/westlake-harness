.class public final Ladapter/activity/J10bAppBootstrap;
.super Ljava/lang/Object;
.source "J10bAppBootstrap.java"


# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Ladapter/activity/J10bAppBootstrap$Callbacks;
    }
.end annotation


# static fields
.field private static volatile sDone:Z


# direct methods
.method static constructor <clinit>()V
    .registers 1

    .line 43
    const/4 v0, 0x0

    sput-boolean v0, Ladapter/activity/J10bAppBootstrap;->sDone:Z

    return-void
.end method

.method private constructor <init>()V
    .registers 1

    .line 41
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method static synthetic access$100(Landroid/app/Activity;)Z
    .registers 1

    .line 40
    invoke-static {p0}, Ladapter/activity/J10bAppBootstrap;->isAppCompatActivity(Landroid/app/Activity;)Z

    move-result p0

    return p0
.end method

.method static declared-synchronized bootstrap()V
    .registers 14

    const-class v0, Ladapter/activity/J10bAppBootstrap;

    monitor-enter v0

    .line 58
    :try_start_3
    sget-boolean v1, Ladapter/activity/J10bAppBootstrap;->sDone:Z
    :try_end_5
    .catchall {:try_start_3 .. :try_end_5} :catchall_105

    if-eqz v1, :cond_9

    monitor-exit v0

    return-void

    .line 60
    :cond_9
    :try_start_9
    const-string v1, "android.app.ActivityThread"

    invoke-static {v1}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v1

    .line 61
    const-string v2, "currentActivityThread"

    const/4 v3, 0x0

    new-array v4, v3, [Ljava/lang/Class;

    invoke-virtual {v1, v2, v4}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v2

    new-array v4, v3, [Ljava/lang/Object;

    const/4 v5, 0x0

    invoke-virtual {v2, v5, v4}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v2

    .line 62
    if-nez v2, :cond_2a

    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v2, "[J10b] no currentActivityThread"

    invoke-virtual {v1, v2}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_28
    .catchall {:try_start_9 .. :try_end_28} :catchall_ea

    monitor-exit v0

    return-void

    .line 64
    :cond_2a
    :try_start_2a
    const-string v4, "mInitialApplication"

    invoke-virtual {v1, v4}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v4

    .line 65
    const/4 v6, 0x1

    invoke-virtual {v4, v6}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    .line 66
    invoke-virtual {v4, v2}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v7

    .line 68
    invoke-static {}, Ladapter/activity/SelfComponentFallback;->boundInfo()Landroid/content/pm/ApplicationInfo;

    move-result-object v8

    .line 69
    if-nez v8, :cond_47

    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v2, "[J10b] no boundInfo (ensureBindApplication not run yet?)"

    invoke-virtual {v1, v2}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_45
    .catchall {:try_start_2a .. :try_end_45} :catchall_ea

    monitor-exit v0

    return-void

    .line 71
    :cond_47
    :try_start_47
    const-string v9, "getPackageInfoNoCheck"

    new-array v10, v6, [Ljava/lang/Class;

    const-class v11, Landroid/content/pm/ApplicationInfo;

    aput-object v11, v10, v3

    invoke-virtual {v1, v9, v10}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v9

    filled-new-array {v8}, [Ljava/lang/Object;

    move-result-object v8

    invoke-virtual {v9, v2, v8}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v8

    .line 72
    const-string v9, "getInstrumentation"

    new-array v10, v3, [Ljava/lang/Class;

    invoke-virtual {v1, v9, v10}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v1

    new-array v9, v3, [Ljava/lang/Object;

    invoke-virtual {v1, v2, v9}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    .line 74
    const-string v9, "android.app.LoadedApk"

    invoke-static {v9}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v9

    .line 75
    const-string v10, "android.app.Instrumentation"

    invoke-static {v10}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v10
    :try_end_75
    .catchall {:try_start_47 .. :try_end_75} :catchall_ea

    .line 78
    :try_start_75
    const-string v11, "makeApplicationInner"

    const/4 v12, 0x2

    new-array v12, v12, [Ljava/lang/Class;

    sget-object v13, Ljava/lang/Boolean;->TYPE:Ljava/lang/Class;

    aput-object v13, v12, v3

    aput-object v10, v12, v6

    invoke-virtual {v9, v11, v12}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v3
    :try_end_84
    .catch Ljava/lang/NoSuchMethodException; {:try_start_75 .. :try_end_84} :catch_cf
    .catchall {:try_start_75 .. :try_end_84} :catchall_ea

    .line 82
    nop

    .line 83
    :try_start_85
    sget-object v9, Ljava/lang/Boolean;->FALSE:Ljava/lang/Boolean;

    filled-new-array {v9, v1}, [Ljava/lang/Object;

    move-result-object v1

    invoke-virtual {v3, v8, v1}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Landroid/app/Application;

    .line 84
    if-nez v1, :cond_9c

    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v2, "[J10b] makeApplicationInner returned null"

    invoke-virtual {v1, v2}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_9a
    .catchall {:try_start_85 .. :try_end_9a} :catchall_ea

    monitor-exit v0

    return-void

    .line 86
    :cond_9c
    if-nez v7, :cond_bd

    .line 87
    :try_start_9e
    invoke-virtual {v4, v2, v1}, Ljava/lang/reflect/Field;->set(Ljava/lang/Object;Ljava/lang/Object;)V

    .line 88
    sget-object v2, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    const-string v4, "[J10b-APP] mInitialApplication set from first Activity "

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v1}, Landroid/app/Application;->getPackageName()Ljava/lang/String;

    move-result-object v4

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-virtual {v2, v3}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 90
    :cond_bd
    new-instance v2, Ladapter/activity/J10bAppBootstrap$Callbacks;

    invoke-direct {v2, v5}, Ladapter/activity/J10bAppBootstrap$Callbacks;-><init>(Ladapter/activity/J10bAppBootstrap$1;)V

    invoke-virtual {v1, v2}, Landroid/app/Application;->registerActivityLifecycleCallbacks(Landroid/app/Application$ActivityLifecycleCallbacks;)V

    .line 91
    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    const-string v2, "[J10b-NOTITLE] installed"

    invoke-virtual {v1, v2}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 92
    sput-boolean v6, Ladapter/activity/J10bAppBootstrap;->sDone:Z

    .line 95
    goto :goto_103

    .line 79
    :catch_cf
    move-exception v1

    .line 80
    sget-object v2, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    const-string v4, "[J10b] makeApplicationInner unavailable, fall back to design-1: "

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v2, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_e8
    .catchall {:try_start_9e .. :try_end_e8} :catchall_ea

    .line 81
    monitor-exit v0

    return-void

    .line 93
    :catchall_ea
    move-exception v1

    .line 94
    :try_start_eb
    sget-object v2, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    const-string v4, "[J10b] bootstrap failed: "

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {v3, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v2, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_103
    .catchall {:try_start_eb .. :try_end_103} :catchall_105

    .line 96
    :goto_103
    monitor-exit v0

    return-void

    .line 57
    :catchall_105
    move-exception v1

    :try_start_106
    monitor-exit v0
    :try_end_107
    .catchall {:try_start_106 .. :try_end_107} :catchall_105

    throw v1
.end method

.method private static isAppCompatActivity(Landroid/app/Activity;)Z
    .registers 3

    .line 99
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object p0

    :goto_4
    if-eqz p0, :cond_26

    const-class v0, Landroid/app/Activity;

    if-eq p0, v0, :cond_26

    .line 100
    invoke-virtual {p0}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object v0

    .line 101
    const-string v1, "androidx.appcompat.app.AppCompatActivity"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-nez v1, :cond_24

    .line 102
    const-string v1, "android.support.v7.app.AppCompatActivity"

    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :cond_1f

    goto :goto_24

    .line 99
    :cond_1f
    invoke-virtual {p0}, Ljava/lang/Class;->getSuperclass()Ljava/lang/Class;

    move-result-object p0

    goto :goto_4

    .line 103
    :cond_24
    :goto_24
    const/4 p0, 0x1

    return p0

    .line 106
    :cond_26
    const/4 p0, 0x0

    return p0
.end method

.method public static schedule()V
    .registers 4

    .line 49
    :try_start_0
    new-instance v0, Landroid/os/Handler;

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v1

    invoke-direct {v0, v1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    new-instance v1, Ladapter/activity/J10bAppBootstrap$1;

    invoke-direct {v1}, Ladapter/activity/J10bAppBootstrap$1;-><init>()V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z
    :try_end_11
    .catchall {:try_start_0 .. :try_end_11} :catchall_12

    .line 54
    goto :goto_2b

    .line 52
    :catchall_12
    move-exception v0

    .line 53
    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "[J10b] schedule failed: "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v1, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 55
    :goto_2b
    return-void
.end method
