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

    .line 134
    return-void
.end method

.method public onActivityDestroyed(Landroid/app/Activity;)V
    .registers 2

    .line 140
    return-void
.end method

.method public onActivityPaused(Landroid/app/Activity;)V
    .registers 2

    .line 137
    return-void
.end method

.method public onActivityPreCreated(Landroid/app/Activity;Landroid/os/Bundle;)V
    .registers 7

    .line 113
    :try_start_0
    # invokes: Ladapter/activity/J10bAppBootstrap;->isAppCompatActivity(Landroid/app/Activity;)Z
    invoke-static {p1}, Ladapter/activity/J10bAppBootstrap;->access$100(Landroid/app/Activity;)Z

    move-result p2
    :try_end_4
    .catchall {:try_start_0 .. :try_end_4} :catchall_72

    if-nez p2, :cond_7

    return-void

    .line 116
    :cond_7
    nop

    .line 118
    const/4 p2, 0x0

    const/4 v0, 0x1

    :try_start_a
    invoke-virtual {p1}, Landroid/app/Activity;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object v1

    const v2, 0x1010056

    const v3, 0x10102cd

    filled-new-array {v3, v2}, [I

    move-result-object v2

    invoke-virtual {v1, v2}, Landroid/content/res/Resources$Theme;->obtainStyledAttributes([I)Landroid/content/res/TypedArray;

    move-result-object v1

    .line 120
    invoke-virtual {v1, p2, v0}, Landroid/content/res/TypedArray;->getBoolean(IZ)Z

    move-result v2
    :try_end_20
    .catchall {:try_start_a .. :try_end_20} :catchall_2a

    .line 121
    :try_start_20
    invoke-virtual {v1, v0, p2}, Landroid/content/res/TypedArray;->getBoolean(IZ)Z

    move-result p2

    .line 122
    invoke-virtual {v1}, Landroid/content/res/TypedArray;->recycle()V
    :try_end_27
    .catchall {:try_start_20 .. :try_end_27} :catchall_28

    goto :goto_2c

    .line 123
    :catchall_28
    move-exception v1

    goto :goto_2c

    :catchall_2a
    move-exception v1

    move v2, v0

    :goto_2c
    nop

    .line 126
    :try_start_2d
    invoke-virtual {p1}, Landroid/app/Activity;->getTheme()Landroid/content/res/Resources$Theme;

    move-result-object v1

    const v3, 0x1030006

    invoke-virtual {v1, v3, v0}, Landroid/content/res/Resources$Theme;->applyStyle(IZ)V

    .line 127
    sget-object v0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "[J10b-NOTITLE] applied "

    invoke-virtual {v1, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v1

    invoke-virtual {p1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/Class;->getName()Ljava/lang/String;

    move-result-object p1

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v1, " (pre: windowActionBar="

    invoke-virtual {p1, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, v2}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string v1, " windowNoTitle="

    invoke-virtual {p1, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1, p2}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object p1

    const-string p2, ")"

    invoke-virtual {p1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object p1

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-virtual {v0, p1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V
    :try_end_71
    .catchall {:try_start_2d .. :try_end_71} :catchall_72

    .line 131
    goto :goto_8b

    .line 129
    :catchall_72
    move-exception p1

    .line 130
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

    .line 132
    :goto_8b
    return-void
.end method

.method public onActivityResumed(Landroid/app/Activity;)V
    .registers 2

    .line 136
    return-void
.end method

.method public onActivitySaveInstanceState(Landroid/app/Activity;Landroid/os/Bundle;)V
    .registers 3

    .line 139
    return-void
.end method

.method public onActivityStarted(Landroid/app/Activity;)V
    .registers 2

    .line 135
    return-void
.end method

.method public onActivityStopped(Landroid/app/Activity;)V
    .registers 2

    .line 138
    return-void
.end method
