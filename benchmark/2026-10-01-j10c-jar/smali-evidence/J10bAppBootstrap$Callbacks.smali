.class final Ladapter/activity/J10bAppBootstrap$Callbacks;
.super Ljava/lang/Object;
.source "J10bAppBootstrap.java"

# interfaces
.implements Landroid/app/Application$ActivityLifecycleCallbacks;


# annotations
.annotation system Ldalvik/annotation/EnclosingClass;
    value = Ladapter/activity/J10bAppBootstrap;
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x1a
    name = "Callbacks"
.end annotation


# direct methods
.method private constructor <init>()V
    .registers 1

    .line 109
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method synthetic constructor <init>(Ladapter/activity/J10bAppBootstrap$1;)V
    .registers 2

    .line 109
    invoke-direct {p0}, Ladapter/activity/J10bAppBootstrap$Callbacks;-><init>()V

    return-void
.end method


# virtual methods
.method public onActivityCreated(Landroid/app/Activity;Landroid/os/Bundle;)V
    .registers 3

    .line 156
    return-void
.end method

.method public onActivityDestroyed(Landroid/app/Activity;)V
    .registers 2

    .line 162
    return-void
.end method

.method public onActivityPaused(Landroid/app/Activity;)V
    .registers 2

    .line 159
    return-void
.end method

.method public onActivityPreCreated(Landroid/app/Activity;Landroid/os/Bundle;)V
    .registers 16

    .line 113
    const-string p2, "@0x"

    const-string v0, " windowNoTitle="

    const-string v1, "attr"

    const-string v2, "n/a"

    :try_start_8
    # invokes: Ladapter/activity/J10bAppBootstrap;->isAppCompatActivity(Landroid/app/Activity;)Z
    invoke-static {p1}, Ladapter/activity/J10bAppBootstrap;->access$100(Landroid/app/Activity;)Z

    move-result v3
    :try_end_c
    .catchall {:try_start_8 .. :try_end_c} :catchall_114

    if-nez v3, :cond_f

    return-void

    .line 115
    :cond_f
    nop

    .line 117
    const v3, 0x1010056

    const v4, 0x10102cd

    const/4 v5, 0x0

    const/4 v6, 0x1

    :try_start_18
    invoke-virtual {p1}, Landroid/app/Activity;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object v7

    filled-new-array {v4, v3}, [I

    move-result-object v8

    invoke-virtual {v7, v8}, Landroid/content/res/Resources$Theme;->obtainStyledAttributes([I)Landroid/content/res/TypedArray;

    move-result-object v7

    .line 119
    invoke-virtual {v7, v5, v6}, Landroid/content/res/TypedArray;->getBoolean(IZ)Z

    move-result v8
    :try_end_28
    .catchall {:try_start_18 .. :try_end_28} :catchall_35

    .line 120
    :try_start_28
    invoke-virtual {v7, v6, v5}, Landroid/content/res/TypedArray;->getBoolean(IZ)Z

    move-result v9
    :try_end_2c
    .catchall {:try_start_28 .. :try_end_2c} :catchall_32

    .line 121
    :try_start_2c
    invoke-virtual {v7}, Landroid/content/res/TypedArray;->recycle()V
    :try_end_2f
    .catchall {:try_start_2c .. :try_end_2f} :catchall_30

    goto :goto_38

    .line 122
    :catchall_30
    move-exception v7

    goto :goto_38

    :catchall_32
    move-exception v7

    move v9, v5

    goto :goto_38

    :catchall_35
    move-exception v7

    move v9, v5

    move v8, v6

    :goto_38
    nop

    .line 128
    nop

    .line 130
    :try_start_3a
    invoke-virtual {p1}, Landroid/app/Activity;->getPackageName()Ljava/lang/String;

    move-result-object v7

    .line 131
    invoke-virtual {p1}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;

    move-result-object v10

    .line 132
    const-string v11, "windowActionBar"

    invoke-virtual {v10, v11, v1, v7}, Landroid/content/res/Resources;->getIdentifier(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)I

    move-result v11

    .line 133
    const-string v12, "windowNoTitle"

    invoke-virtual {v10, v12, v1, v7}, Landroid/content/res/Resources;->getIdentifier(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)I

    move-result v1

    .line 134
    if-nez v11, :cond_56

    if-eqz v1, :cond_53

    goto :goto_56

    :cond_53
    move-object p2, v2

    goto/16 :goto_be

    .line 135
    :cond_56
    :goto_56
    invoke-virtual {p1}, Landroid/app/Activity;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object v7

    .line 136
    if-eqz v11, :cond_5d

    move v4, v11

    .line 137
    :cond_5d
    if-eqz v1, :cond_60

    move v3, v1

    :cond_60
    filled-new-array {v4, v3}, [I

    move-result-object v3

    .line 135
    invoke-virtual {v7, v3}, Landroid/content/res/Resources$Theme;->obtainStyledAttributes([I)Landroid/content/res/TypedArray;

    move-result-object v3

    .line 138
    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4}, Ljava/lang/StringBuilder;-><init>()V
    :try_end_6d
    .catchall {:try_start_3a .. :try_end_6d} :catchall_bc

    const-string v7, "noid"

    if-eqz v11, :cond_7a

    :try_start_71
    invoke-virtual {v3, v5, v6}, Landroid/content/res/TypedArray;->getBoolean(IZ)Z

    move-result v10

    invoke-static {v10}, Ljava/lang/String;->valueOf(Z)Ljava/lang/String;

    move-result-object v10

    goto :goto_7b

    :cond_7a
    move-object v10, v7

    :goto_7b
    invoke-virtual {v4, v10}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    invoke-virtual {v4, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    .line 139
    invoke-static {v11}, Ljava/lang/Integer;->toHexString(I)Ljava/lang/String;

    move-result-object v10

    invoke-virtual {v4, v10}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v4

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v4
    :try_end_8f
    .catchall {:try_start_71 .. :try_end_8f} :catchall_bc

    .line 140
    :try_start_8f
    new-instance v10, Ljava/lang/StringBuilder;

    invoke-direct {v10}, Ljava/lang/StringBuilder;-><init>()V

    if-eqz v1, :cond_9e

    invoke-virtual {v3, v6, v5}, Landroid/content/res/TypedArray;->getBoolean(IZ)Z

    move-result v5

    invoke-static {v5}, Ljava/lang/String;->valueOf(Z)Ljava/lang/String;

    move-result-object v7

    :cond_9e
    invoke-virtual {v10, v7}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v5

    invoke-virtual {v5, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p2

    .line 141
    invoke-static {v1}, Ljava/lang/Integer;->toHexString(I)Ljava/lang/String;

    move-result-object v1

    invoke-virtual {p2, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p2

    invoke-virtual {p2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    .line 142
    invoke-virtual {v3}, Landroid/content/res/TypedArray;->recycle()V
    :try_end_b5
    .catchall {:try_start_8f .. :try_end_b5} :catchall_b8

    move-object p2, v2

    move-object v2, v4

    goto :goto_be

    .line 144
    :catchall_b8
    move-exception p2

    move-object p2, v2

    move-object v2, v4

    goto :goto_be

    :catchall_bc
    move-exception p2

    move-object p2, v2

    :goto_be
    nop

    .line 147
    :try_start_bf
    invoke-virtual {p1}, Landroid/app/Activity;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object v1

    const v3, 0x1030006

    invoke-virtual {v1, v3, v6}, Landroid/content/res/Resources$Theme;->applyStyle(IZ)V

    .line 148
    sget-object v1, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    const-string v4, "[J10b-NOTITLE] applied "

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v3

    invoke-virtual {p1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object p1

    invoke-virtual {v3, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v3, " (platform windowActionBar="

    invoke-virtual {p1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, v8}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, v9}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v3, "; app windowActionBar="

    invoke-virtual {p1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string p2, ")"

    invoke-virtual {p1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-virtual {v1, p1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_113
    .catchall {:try_start_bf .. :try_end_113} :catchall_114

    .line 153
    goto :goto_12d

    .line 151
    :catchall_114
    move-exception p1

    .line 152
    sget-object p2, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "[J10b-NOTITLE] apply failed: "

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-virtual {p2, p1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    .line 154
    :goto_12d
    return-void
.end method

.method public onActivityResumed(Landroid/app/Activity;)V
    .registers 2

    .line 158
    return-void
.end method

.method public onActivitySaveInstanceState(Landroid/app/Activity;Landroid/os/Bundle;)V
    .registers 3

    .line 161
    return-void
.end method

.method public onActivityStarted(Landroid/app/Activity;)V
    .registers 2

    .line 157
    return-void
.end method

.method public onActivityStopped(Landroid/app/Activity;)V
    .registers 2

    .line 160
    return-void
.end method
