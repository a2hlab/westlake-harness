.class public final Ladapter/activity/SelfActivityInfoSynthesis;
.super Ljava/lang/Object;
.source "SelfActivityInfoSynthesis.java"


# direct methods
.method private constructor <init>()V
    .registers 1

    .line 35
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method private static activityTheme(Landroid/content/ComponentName;)I
    .registers 7

    .line 89
    const/4 v0, 0x0

    :try_start_1
    const-string v1, "adapter.activity.ManifestJsonFallback"

    invoke-static {v1}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v1

    .line 90
    const-string v2, "activityTheme"

    const/4 v3, 0x2

    new-array v3, v3, [Ljava/lang/Class;

    const-class v4, Ljava/lang/String;

    aput-object v4, v3, v0

    const-class v4, Ljava/lang/String;

    const/4 v5, 0x1

    aput-object v4, v3, v5

    invoke-virtual {v1, v2, v3}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v1

    .line 91
    invoke-virtual {p0}, Landroid/content/ComponentName;->getPackageName()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {p0}, Landroid/content/ComponentName;->getClassName()Ljava/lang/String;

    move-result-object p0

    filled-new-array {v2, p0}, [Ljava/lang/Object;

    move-result-object p0

    const/4 v2, 0x0

    invoke-virtual {v1, v2, p0}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p0

    .line 92
    instance-of v1, p0, Ljava/lang/Integer;

    if-eqz v1, :cond_34

    check-cast p0, Ljava/lang/Integer;

    invoke-virtual {p0}, Ljava/lang/Integer;->intValue()I

    move-result v0
    :try_end_34
    .catchall {:try_start_1 .. :try_end_34} :catchall_35

    :cond_34
    return v0

    .line 93
    :catchall_35
    move-exception p0

    .line 94
    return v0
.end method

.method private static boundSelf()Ljava/lang/Object;
    .registers 3

    .line 100
    const/4 v0, 0x0

    :try_start_1
    const-string v1, "adapter.activity.SelfComponentFallback"

    invoke-static {v1}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;

    move-result-object v1

    .line 101
    const-string v2, "bound"

    invoke-virtual {v1, v2}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v1

    .line 102
    const/4 v2, 0x1

    invoke-virtual {v1, v2}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    .line 103
    invoke-virtual {v1, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v0
    :try_end_15
    .catchall {:try_start_1 .. :try_end_15} :catchall_16

    return-object v0

    .line 104
    :catchall_16
    move-exception v1

    .line 105
    return-object v0
.end method

.method public static maybe(Ljava/lang/reflect/Method;[Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
    .registers 8

    .line 39
    const/4 v0, 0x0

    if-eqz p0, :cond_d0

    if-eqz p2, :cond_7

    goto/16 :goto_d0

    .line 40
    :cond_7
    :try_start_7
    const-string p2, "getActivityInfo"

    invoke-virtual {p0}, Ljava/lang/reflect/Method;->getName()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {p2, p0}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p0

    if-nez p0, :cond_14

    return-object v0

    .line 41
    :cond_14
    if-eqz p1, :cond_b5

    array-length p0, p1

    const/4 p2, 0x1

    if-lt p0, p2, :cond_b5

    const/4 p0, 0x0

    aget-object v1, p1, p0

    instance-of v1, v1, Landroid/content/ComponentName;

    if-nez v1, :cond_23

    goto/16 :goto_b5

    .line 42
    :cond_23
    aget-object v1, p1, p0

    check-cast v1, Landroid/content/ComponentName;

    .line 43
    array-length v2, p1

    const/4 v3, 0x2

    if-lt v2, v3, :cond_3a

    aget-object v2, p1, p2

    instance-of v2, v2, Ljava/lang/Long;

    if-eqz v2, :cond_3a

    aget-object p1, p1, p2

    check-cast p1, Ljava/lang/Long;

    invoke-virtual {p1}, Ljava/lang/Long;->longValue()J

    move-result-wide p1

    goto :goto_3c

    :cond_3a
    const-wide/16 p1, 0x0

    .line 46
    :goto_3c
    invoke-static {}, Ladapter/activity/SelfActivityInfoSynthesis;->boundSelf()Ljava/lang/Object;

    move-result-object v2

    .line 47
    if-nez v2, :cond_44

    move-object v3, v0

    goto :goto_4a

    :cond_44
    const-string v3, "packageName"

    invoke-static {v2, v3}, Ladapter/activity/SelfActivityInfoSynthesis;->stringField(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v3

    .line 48
    :goto_4a
    if-eqz v3, :cond_b4

    invoke-virtual {v1}, Landroid/content/ComponentName;->getPackageName()Ljava/lang/String;

    move-result-object v4

    invoke-virtual {v3, v4}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v3

    if-nez v3, :cond_57

    goto :goto_b4

    .line 49
    :cond_57
    invoke-static {v2}, Ladapter/activity/SelfActivityInfoSynthesis;->uidField(Ljava/lang/Object;)I

    move-result v2

    invoke-static {}, Landroid/os/Process;->myUid()I

    move-result v3

    if-eq v2, v3, :cond_62

    return-object v0

    .line 51
    :cond_62
    invoke-static {v1, p1, p2}, Ladapter/activity/SelfActivityInfoSynthesis;->synthFromManifest(Landroid/content/ComponentName;J)Landroid/content/pm/ActivityInfo;

    move-result-object p1

    .line 52
    if-eqz p1, :cond_b3

    .line 54
    invoke-static {v1}, Ladapter/activity/SelfActivityInfoSynthesis;->activityTheme(Landroid/content/ComponentName;)I

    move-result p2

    .line 55
    if-eqz p2, :cond_70

    iput p2, p1, Landroid/content/pm/ActivityInfo;->theme:I

    .line 56
    :cond_70
    sget-object p2, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "[J10-ACTINFO] synthesized self getActivityInfo "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v2

    .line 57
    invoke-virtual {v1}, Landroid/content/ComponentName;->flattenToShortString()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, " theme=0x"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    iget v2, p1, Landroid/content/pm/ActivityInfo;->theme:I

    invoke-static {v2}, Ljava/lang/Integer;->toHexString(I)Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    const-string v2, " metaData="

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    .line 58
    iget-object v2, p1, Landroid/content/pm/ActivityInfo;->metaData:Landroid/os/Bundle;

    if-nez v2, :cond_a0

    :goto_9f
    goto :goto_a7

    :cond_a0
    iget-object p0, p1, Landroid/content/pm/ActivityInfo;->metaData:Landroid/os/Bundle;

    invoke-virtual {p0}, Landroid/os/Bundle;->size()I

    move-result p0

    goto :goto_9f

    :goto_a7
    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    .line 56
    invoke-virtual {p2, p0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_b2
    .catchall {:try_start_7 .. :try_end_b2} :catchall_b6

    .line 59
    return-object p1

    .line 63
    :cond_b3
    goto :goto_cf

    .line 48
    :cond_b4
    :goto_b4
    return-object v0

    .line 41
    :cond_b5
    :goto_b5
    return-object v0

    .line 61
    :catchall_b6
    move-exception p0

    .line 62
    sget-object p1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance p2, Ljava/lang/StringBuilder;

    invoke-direct {p2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "[J10-ACTINFO] synth failed: "

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p2

    invoke-virtual {p2, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {p1, p0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 64
    :goto_cf
    return-object v0

    .line 39
    :cond_d0
    :goto_d0
    return-object v0
.end method

.method private static stringField(Ljava/lang/Object;Ljava/lang/String;)Ljava/lang/String;
    .registers 4

    .line 111
    const/4 v0, 0x0

    :try_start_1
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v1

    invoke-virtual {v1, p1}, Ljava/lang/Class;->getField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object p1

    .line 112
    invoke-virtual {p1, p0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object p0

    .line 113
    instance-of p1, p0, Ljava/lang/String;

    if-eqz p1, :cond_14

    check-cast p0, Ljava/lang/String;
    :try_end_13
    .catchall {:try_start_1 .. :try_end_13} :catchall_15

    move-object v0, p0

    :cond_14
    return-object v0

    .line 114
    :catchall_15
    move-exception p0

    .line 115
    return-object v0
.end method

.method private static synthFromManifest(Landroid/content/ComponentName;J)Landroid/content/pm/ActivityInfo;
    .registers 11

    .line 76
    const/4 v1, 0x0

    :try_start_1
    invoke-virtual {p0}, Landroid/content/ComponentName;->getPackageName()Ljava/lang/String;

    move-result-object v0

    invoke-static {v0}, Ladapter/activity/SelfComponentFallback;->projectionFor(Ljava/lang/String;)Ladapter/activity/ManifestComponentProjection;

    move-result-object v2

    .line 77
    if-nez v2, :cond_c

    return-object v1

    .line 78
    :cond_c
    invoke-static {}, Ladapter/activity/SelfComponentFallback;->boundInfo()Landroid/content/pm/ApplicationInfo;

    move-result-object v5

    .line 79
    invoke-virtual {p0}, Landroid/content/ComponentName;->getClassName()Ljava/lang/String;

    move-result-object v3

    const-string v4, "activity"

    move-wide v6, p1

    invoke-virtual/range {v2 .. v7}, Ladapter/activity/ManifestComponentProjection;->component(Ljava/lang/String;Ljava/lang/String;Landroid/content/pm/ApplicationInfo;J)Landroid/content/pm/ComponentInfo;

    move-result-object p0

    .line 80
    instance-of p1, p0, Landroid/content/pm/ActivityInfo;

    if-eqz p1, :cond_22

    check-cast p0, Landroid/content/pm/ActivityInfo;
    :try_end_21
    .catchall {:try_start_1 .. :try_end_21} :catchall_23

    return-object p0

    .line 83
    :cond_22
    goto :goto_3d

    .line 81
    :catchall_23
    move-exception v0

    move-object p0, v0

    .line 82
    sget-object p1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance p2, Ljava/lang/StringBuilder;

    invoke-direct {p2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v0, "[J10-ACTINFO] manifest activity lookup failed: "

    invoke-virtual {p2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p2

    invoke-virtual {p2, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object p0

    invoke-virtual {p0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-virtual {p1, p0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 84
    :goto_3d
    return-object v1
.end method

.method private static uidField(Ljava/lang/Object;)I
    .registers 3

    .line 121
    :try_start_0
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v0

    const-string v1, "uid"

    invoke-virtual {v0, v1}, Ljava/lang/Class;->getField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v0

    .line 122
    invoke-virtual {v0, p0}, Ljava/lang/reflect/Field;->getInt(Ljava/lang/Object;)I

    move-result p0
    :try_end_e
    .catchall {:try_start_0 .. :try_end_e} :catchall_f

    return p0

    .line 123
    :catchall_f
    move-exception p0

    .line 124
    const/4 p0, -0x1

    return p0
.end method
