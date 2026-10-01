.class public final Ladapter/core/OHEnvironment;
.super Ljava/lang/Object;
.source "OHEnvironment.java"


# static fields
.field private static final PROP_OH_ADAPTER_ENABLED:Ljava/lang/String; = "persist.oh.adapter.enabled"

.field private static final TAG:Ljava/lang/String; = "OHEnvironment"


# direct methods
.method static constructor <clinit>()V
    .registers 1

    const-string v0, "oh_adapter_bridge"

    .line 22
    invoke-static {v0}, Ljava/lang/System;->loadLibrary(Ljava/lang/String;)V

    return-void
.end method

.method private constructor <init>()V
    .registers 1

    .line 25
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static attachApplication(Ljava/lang/Object;IILjava/lang/String;)Z
    .registers 4

    .line 86
    invoke-static {p0, p1, p2, p3}, Ladapter/core/OHEnvironment;->nativeAttachApplication(Ljava/lang/Object;IILjava/lang/String;)Z

    move-result p0

    return p0
.end method

.method public static getActivityManagerAdapter()Ljava/lang/Object;
    .registers 1

    const-string v0, "adapter.activity.ActivityManagerAdapter"

    .line 177
    invoke-static {v0}, Ladapter/core/OHEnvironment;->newAdapterReflective(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    return-object v0
.end method

.method public static getActivityTaskManagerAdapter()Ljava/lang/Object;
    .registers 1

    const-string v0, "adapter.activity.ActivityTaskManagerAdapter"

    .line 182
    invoke-static {v0}, Ladapter/core/OHEnvironment;->newAdapterReflective(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    return-object v0
.end method

.method public static getPackageManagerAdapter()Ljava/lang/Object;
    .registers 1

    const-string v0, "adapter.packagemanager.PackageManagerAdapter"

    .line 187
    invoke-static {v0}, Ladapter/core/OHEnvironment;->newAdapterReflective(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    return-object v0
.end method

.method public static getWindowManagerAdapter()Ljava/lang/Object;
    .registers 1

    const-string v0, "adapter.window.WindowManagerAdapter"

    .line 192
    invoke-static {v0}, Ladapter/core/OHEnvironment;->newAdapterReflective(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    return-object v0
.end method

.method public static getWindowSessionAdapter()Ljava/lang/Object;
    .registers 1

    const-string v0, "adapter.window.WindowSessionAdapter"

    .line 197
    invoke-static {v0}, Ladapter/core/OHEnvironment;->newAdapterReflective(Ljava/lang/String;)Ljava/lang/Object;

    move-result-object v0

    return-object v0
.end method

.method public static initialize()V
    .registers 0

    .line 53
    invoke-static {}, Ladapter/core/OHEnvironment;->nativeInitialize()Z

    .line 54
    invoke-static {}, Ladapter/core/OHEnvironment;->nativeConnectToOHServices()Z

    return-void
.end method

.method public static isOHEnvironment()Z
    .registers 2

    const-string v0, "persist.oh.adapter.enabled"

    .line 34
    invoke-static {v0}, Landroid/os/SystemProperties;->get(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    const-string v1, "true"

    .line 35
    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-eqz v1, :cond_10

    const/4 v0, 0x1

    return v0

    :cond_10
    const-string v1, "false"

    .line 38
    invoke-virtual {v1, v0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v0

    if-eqz v0, :cond_1a

    const/4 v0, 0x0

    return v0

    .line 42
    :cond_1a
    invoke-static {}, Ladapter/core/OHEnvironment;->nativeIsOHEnvironment()Z

    move-result v0

    return v0
.end method

.method public static native nativeAttachApplication(Ljava/lang/Object;IILjava/lang/String;)Z
.end method

.method public static native nativeConnectToOHServices()Z
.end method

.method public static native nativeInitialize()Z
.end method

.method public static native nativeIsOHEnvironment()Z
.end method

.method public static native nativeNotifyAppState(I)V
.end method

.method public static native nativeShutdown()V
.end method

.method private static newAdapterReflective(Ljava/lang/String;)Ljava/lang/Object;
    .registers 7

    const/4 v0, 0x0

    const/4 v1, 0x0

    .line 149
    :try_start_2
    invoke-static {}, Ljava/lang/ClassLoader;->getSystemClassLoader()Ljava/lang/ClassLoader;

    move-result-object v2

    if-eqz v2, :cond_22

    .line 150
    const-class v3, Ladapter/core/OHEnvironment;

    invoke-virtual {v3}, Ljava/lang/Class;->getClassLoader()Ljava/lang/ClassLoader;

    move-result-object v3

    if-eq v2, v3, :cond_22

    const/4 v3, 0x1

    .line 151
    invoke-static {p0, v3, v2}, Ljava/lang/Class;->forName(Ljava/lang/String;ZLjava/lang/ClassLoader;)Ljava/lang/Class;

    move-result-object v2

    new-array v3, v0, [Ljava/lang/Class;

    .line 152
    invoke-virtual {v2, v3}, Ljava/lang/Class;->getDeclaredConstructor([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;

    move-result-object v2

    new-array v3, v0, [Ljava/lang/Object;

    invoke-virtual {v2, v3}, Ljava/lang/reflect/Constructor;->newInstance([Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p0
    :try_end_21
    .catchall {:try_start_2 .. :try_end_21} :catchall_24

    return-object p0

    :cond_22
    move-object v2, v1

    goto :goto_25

    :catchall_24
    move-exception v2

    .line 159
    :goto_25
    :try_start_25
    invoke-static {p0}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v3

    new-array v4, v0, [Ljava/lang/Class;

    .line 160
    invoke-virtual {v3, v4}, Ljava/lang/Class;->getDeclaredConstructor([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;

    move-result-object v3

    new-array v0, v0, [Ljava/lang/Object;

    invoke-virtual {v3, v0}, Ljava/lang/reflect/Constructor;->newInstance([Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p0
    :try_end_35
    .catchall {:try_start_25 .. :try_end_35} :catchall_36

    return-object p0

    :catchall_36
    move-exception v0

    .line 166
    sget-object v3, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v4, Ljava/lang/StringBuilder;

    const-string v5, "[OHEnvironment] newAdapterReflective("

    invoke-direct {v4, v5}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v4, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string p0, ") both schemes failed"

    invoke-virtual {v4, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {v3, p0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    if-eqz v2, :cond_64

    .line 168
    sget-object p0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v3, Ljava/lang/StringBuilder;

    const-string v4, "  Path A (system CL): "

    invoke-direct {v3, v4}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {p0, v2}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 170
    :cond_64
    sget-object p0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v2, Ljava/lang/StringBuilder;

    const-string v3, "  Path B (BCP CL): "

    invoke-direct {v2, v3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-virtual {p0, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    return-object v1
.end method

.method public static shutdown()V
    .registers 0

    .line 97
    invoke-static {}, Ladapter/core/OHEnvironment;->nativeShutdown()V

    return-void
.end method
