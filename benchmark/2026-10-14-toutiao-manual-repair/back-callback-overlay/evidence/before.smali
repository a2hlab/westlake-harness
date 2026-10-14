.class public final Ladapter/activity/ActivityClientControllerAdapter;
.super Landroid/app/IActivityClientController$Stub;
.source "ActivityClientControllerAdapter.java"


# static fields
.field private static final OH_STATE_BACKGROUND:I = 0xa

.field private static final OH_STATE_FOREGROUND:I = 0x9

.field private static final OH_STATE_INACTIVE:I = 0x1

.field private static final TAG:Ljava/lang/String; = "OH_ACCAdapter"

.field private static final sFgReported:Ljava/util/WeakHashMap;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/WeakHashMap<",
            "Landroid/os/IBinder;",
            "Ljava/lang/Boolean;",
            ">;"
        }
    .end annotation
.end field

.field private static volatile sInstance:Ladapter/activity/ActivityClientControllerAdapter;


# direct methods
.method static bridge synthetic -$$Nest$mreportOhLifecycle(Ladapter/activity/ActivityClientControllerAdapter;Landroid/os/IBinder;ILjava/lang/String;)V
    .registers 4

    invoke-direct {p0, p1, p2, p3}, Ladapter/activity/ActivityClientControllerAdapter;->reportOhLifecycle(Landroid/os/IBinder;ILjava/lang/String;)V

    return-void
.end method

.method static bridge synthetic -$$Nest$sfgetsFgReported()Ljava/util/WeakHashMap;
    .registers 1

    sget-object v0, Ladapter/activity/ActivityClientControllerAdapter;->sFgReported:Ljava/util/WeakHashMap;

    return-object v0
.end method

.method static constructor <clinit>()V
    .registers 1

    new-instance v0, Ljava/util/WeakHashMap;

    invoke-direct {v0}, Ljava/util/WeakHashMap;-><init>()V

    sput-object v0, Ladapter/activity/ActivityClientControllerAdapter;->sFgReported:Ljava/util/WeakHashMap;

    return-void
.end method

.method public constructor <init>()V
    .registers 2

    invoke-direct {p0}, Landroid/app/IActivityClientController$Stub;-><init>()V

    const-string p0, "OH_ACCAdapter"

    const-string v0, "ActivityClientControllerAdapter created (extends Stub)"

    invoke-static {p0, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    return-void
.end method

.method public static getInstance()Ladapter/activity/ActivityClientControllerAdapter;
    .registers 2

    sget-object v0, Ladapter/activity/ActivityClientControllerAdapter;->sInstance:Ladapter/activity/ActivityClientControllerAdapter;

    if-nez v0, :cond_17

    const-class v0, Ladapter/activity/ActivityClientControllerAdapter;

    monitor-enter v0

    :try_start_7
    sget-object v1, Ladapter/activity/ActivityClientControllerAdapter;->sInstance:Ladapter/activity/ActivityClientControllerAdapter;

    if-nez v1, :cond_12

    new-instance v1, Ladapter/activity/ActivityClientControllerAdapter;

    invoke-direct {v1}, Ladapter/activity/ActivityClientControllerAdapter;-><init>()V

    sput-object v1, Ladapter/activity/ActivityClientControllerAdapter;->sInstance:Ladapter/activity/ActivityClientControllerAdapter;

    :cond_12
    monitor-exit v0

    goto :goto_17

    :catchall_14
    move-exception v1

    monitor-exit v0
    :try_end_16
    .catchall {:try_start_7 .. :try_end_16} :catchall_14

    throw v1

    :cond_17
    :goto_17
    sget-object v0, Ladapter/activity/ActivityClientControllerAdapter;->sInstance:Ladapter/activity/ActivityClientControllerAdapter;

    return-object v0
.end method

.method private static native nativeAbilityTransitionDone(JI)I
.end method

.method private static native nativeTerminateAbilityByTokenAddr(JI)I
.end method

.method static reportInactiveHeartbeatForToken(Landroid/os/IBinder;)V
    .registers 9

    const-string v0, "W9 onActivityStarted: OH AbilityTransitionDone(token=0x"

    const-string v1, "W9 onActivityStarted: no OH token mapping for "

    const-string v2, "OH_ACCAdapter"

    if-nez p0, :cond_e

    const-string p0, "W9 reportInactiveHeartbeatForToken: null token"

    invoke-static {v2, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    return-void

    :cond_e
    :try_start_e
    invoke-static {p0}, Ladapter/core/OhTokenRegistry;->findOhToken(Landroid/os/IBinder;)Ljava/lang/Long;

    move-result-object v3

    if-eqz v3, :cond_47

    invoke-virtual {v3}, Ljava/lang/Long;->longValue()J

    move-result-wide v4

    const-wide/16 v6, 0x0

    cmp-long v4, v4, v6

    if-eqz v4, :cond_47

    invoke-virtual {v3}, Ljava/lang/Long;->longValue()J

    move-result-wide v4

    const/4 p0, 0x1

    invoke-static {v4, v5, p0}, Ladapter/activity/ActivityClientControllerAdapter;->nativeAbilityTransitionDone(JI)I

    move-result p0

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v3}, Ljava/lang/Long;->longValue()J

    move-result-wide v3

    invoke-static {v3, v4}, Ljava/lang/Long;->toHexString(J)Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v0, ", state=INACTIVE=1) rc="

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v2, p0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_5d

    :cond_47
    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0, v1}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v0, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    invoke-static {v2, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_56
    .catchall {:try_start_e .. :try_end_56} :catchall_57

    goto :goto_5d

    :catchall_57
    move-exception p0

    const-string v0, "W9 onActivityStarted INACTIVE heartbeat failed"

    invoke-static {v2, v0, p0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_5d
    return-void
.end method

.method private reportOhLifecycle(Landroid/os/IBinder;ILjava/lang/String;)V
    .registers 9

    const-string p0, "OH_ACCAdapter"

    :try_start_2
    invoke-static {p1}, Ladapter/core/OhTokenRegistry;->findOhToken(Landroid/os/IBinder;)Ljava/lang/Long;

    move-result-object v0

    if-eqz v0, :cond_4a

    invoke-virtual {v0}, Ljava/lang/Long;->longValue()J

    move-result-wide v1

    const-wide/16 v3, 0x0

    cmp-long v1, v1, v3

    if-eqz v1, :cond_4a

    invoke-virtual {v0}, Ljava/lang/Long;->longValue()J

    move-result-wide v1

    invoke-static {v1, v2, p2}, Ladapter/activity/ActivityClientControllerAdapter;->nativeAbilityTransitionDone(JI)I

    move-result p1

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v1, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v2, ": OH AbilityTransitionDone(token=0x"

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Ljava/lang/Long;->longValue()J

    move-result-wide v2

    invoke-static {v2, v3}, Ljava/lang/Long;->toHexString(J)Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v0, ", state="

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1, p2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string p2, ") rc="

    invoke-virtual {v1, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {p0, p1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_77

    :cond_4a
    new-instance p2, Ljava/lang/StringBuilder;

    invoke-direct {p2}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {p2, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v0, ": no OH token mapping for "

    invoke-virtual {p2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {p2, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {p2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {p0, p1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_61
    .catchall {:try_start_2 .. :try_end_61} :catchall_62

    goto :goto_77

    :catchall_62
    move-exception p1

    new-instance p2, Ljava/lang/StringBuilder;

    invoke-direct {p2}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {p2, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string p3, " reverse callback failed"

    invoke-virtual {p2, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {p2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p2

    invoke-static {p0, p2, p1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_77
    return-void
.end method

.method private static scheduleLocalDestroy(Landroid/os/IBinder;)V
    .registers 3

    new-instance v0, Landroid/os/Handler;

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v1

    invoke-direct {v0, v1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    new-instance v1, Ladapter/activity/ActivityClientControllerAdapter$4;

    invoke-direct {v1, p0}, Ladapter/activity/ActivityClientControllerAdapter$4;-><init>(Landroid/os/IBinder;)V

    invoke-virtual {v0, v1}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    return-void
.end method


# virtual methods
.method public activityDestroyed(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public activityIdle(Landroid/os/IBinder;Landroid/content/res/Configuration;Z)V
    .registers 4

    return-void
.end method

.method public activityLocalRelaunch(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public activityPaused(Landroid/os/IBinder;)V
    .registers 4

    const/4 v0, 0x1

    const-string v1, "activityPaused"

    invoke-direct {p0, p1, v0, v1}, Ladapter/activity/ActivityClientControllerAdapter;->reportOhLifecycle(Landroid/os/IBinder;ILjava/lang/String;)V

    return-void
.end method

.method public activityRefreshed(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public activityRelaunched(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public activityResumed(Landroid/os/IBinder;Z)V
    .registers 11

    const-string p2, "activityResumed: OnDrawListener attached, FG deferred to first frame (token="

    sget-object v0, Ljava/lang/System;->err:Ljava/io/PrintStream;

    new-instance v1, Ljava/lang/StringBuilder;

    const-string v2, "[ABILITY38-RESUMED] uptime="

    invoke-direct {v1, v2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-static {}, Landroid/os/SystemClock;->uptimeMillis()J

    move-result-wide v2

    invoke-virtual {v1, v2, v3}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;

    const-string v2, " token="

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v0, v1}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V

    if-nez p1, :cond_2b

    const-string p0, "OH_ACCAdapter"

    const-string p1, "activityResumed: null token"

    invoke-static {p0, p1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    return-void

    :cond_2b
    const/4 v0, 0x1

    invoke-static {p1, v0}, Ladapter/activity/LifecycleAdapter;->setAppVisibilityOnMain(Landroid/os/IBinder;Z)V

    sget-object v1, Ladapter/activity/ActivityClientControllerAdapter;->sFgReported:Ljava/util/WeakHashMap;

    monitor-enter v1

    :try_start_32
    sget-object v2, Ljava/lang/Boolean;->TRUE:Ljava/lang/Boolean;

    invoke-virtual {v1, p1}, Ljava/util/WeakHashMap;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v3

    invoke-virtual {v2, v3}, Ljava/lang/Boolean;->equals(Ljava/lang/Object;)Z

    move-result v2

    if-eqz v2, :cond_47

    const-string p2, "activityResumed (re-resume)"

    const/16 v0, 0x9

    invoke-direct {p0, p1, v0, p2}, Ladapter/activity/ActivityClientControllerAdapter;->reportOhLifecycle(Landroid/os/IBinder;ILjava/lang/String;)V

    monitor-exit v1

    return-void

    :cond_47
    monitor-exit v1
    :try_end_48
    .catchall {:try_start_32 .. :try_end_48} :catchall_f3

    new-array v1, v0, [Z

    const/4 v2, 0x0

    aput-boolean v2, v1, v2

    new-instance v3, Ladapter/activity/ActivityClientControllerAdapter$1;

    invoke-direct {v3, p0, v1, p1}, Ladapter/activity/ActivityClientControllerAdapter$1;-><init>(Ladapter/activity/ActivityClientControllerAdapter;[ZLandroid/os/IBinder;)V

    :try_start_52
    invoke-static {}, Landroid/app/ActivityThread;->currentActivityThread()Landroid/app/ActivityThread;

    move-result-object v1

    if-eqz v1, :cond_d0

    const-class v4, Landroid/app/ActivityThread;

    const-string v5, "mActivities"

    invoke-virtual {v4, v5}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v4

    invoke-virtual {v4, v0}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    invoke-virtual {v4, v1}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    invoke-virtual {v1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v4

    const-string v5, "get"

    new-array v6, v0, [Ljava/lang/Class;

    const-class v7, Ljava/lang/Object;

    aput-object v7, v6, v2

    invoke-virtual {v4, v5, v6}, Ljava/lang/Class;->getMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v4

    filled-new-array {p1}, [Ljava/lang/Object;

    move-result-object v5

    invoke-virtual {v4, v1, v5}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    if-eqz v1, :cond_d0

    invoke-virtual {v1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    move-result-object v4

    const-string v5, "activity"

    invoke-virtual {v4, v5}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;

    move-result-object v4

    invoke-virtual {v4, v0}, Ljava/lang/reflect/Field;->setAccessible(Z)V

    invoke-virtual {v4, v1}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Landroid/app/Activity;

    if-eqz v1, :cond_d0

    invoke-virtual {v1}, Landroid/app/Activity;->getWindow()Landroid/view/Window;

    move-result-object v4

    if-eqz v4, :cond_d0

    invoke-virtual {v1}, Landroid/app/Activity;->getWindow()Landroid/view/Window;

    move-result-object v1

    invoke-virtual {v1}, Landroid/view/Window;->getDecorView()Landroid/view/View;

    move-result-object v1

    if-eqz v1, :cond_d0

    new-array v4, v0, [Landroid/view/ViewTreeObserver$OnDrawListener;

    new-instance v5, Ladapter/activity/ActivityClientControllerAdapter$2;

    invoke-direct {v5, p0, v1, v4, v3}, Ladapter/activity/ActivityClientControllerAdapter$2;-><init>(Ladapter/activity/ActivityClientControllerAdapter;Landroid/view/View;[Landroid/view/ViewTreeObserver$OnDrawListener;Ljava/lang/Runnable;)V

    aput-object v5, v4, v2

    new-instance v5, Ladapter/activity/ActivityClientControllerAdapter$3;

    invoke-direct {v5, p0, v1, v4}, Ladapter/activity/ActivityClientControllerAdapter$3;-><init>(Ladapter/activity/ActivityClientControllerAdapter;Landroid/view/View;[Landroid/view/ViewTreeObserver$OnDrawListener;)V

    invoke-virtual {v1, v5}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z
    :try_end_b7
    .catchall {:try_start_52 .. :try_end_b7} :catchall_d2

    :try_start_b7
    const-string p0, "OH_ACCAdapter"

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1, p2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    const-string p1, ")"

    invoke-virtual {v1, p1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {p0, p1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_cd
    .catchall {:try_start_b7 .. :try_end_cd} :catchall_ce

    goto :goto_db

    :catchall_ce
    move-exception p0

    goto :goto_d4

    :cond_d0
    move v0, v2

    goto :goto_db

    :catchall_d2
    move-exception p0

    move v0, v2

    :goto_d4
    const-string p1, "OH_ACCAdapter"

    const-string p2, "activityResumed: OnDrawListener setup failed, falling back to 800ms timeout"

    invoke-static {p1, p2, p0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_db
    new-instance p0, Landroid/os/Handler;

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object p1

    invoke-direct {p0, p1}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    const-wide/16 p1, 0x320

    invoke-virtual {p0, v3, p1, p2}, Landroid/os/Handler;->postDelayed(Ljava/lang/Runnable;J)Z

    if-nez v0, :cond_f2

    const-string p0, "OH_ACCAdapter"

    const-string p1, "activityResumed: no OnDrawListener attached, relying on 800ms timeout for FG report"

    invoke-static {p0, p1}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    :cond_f2
    return-void

    :catchall_f3
    move-exception p0

    :try_start_f4
    monitor-exit v1
    :try_end_f5
    .catchall {:try_start_f4 .. :try_end_f5} :catchall_f3

    throw p0
.end method

.method public activityStopped(Landroid/os/IBinder;Landroid/os/Bundle;Landroid/os/PersistableBundle;Ljava/lang/CharSequence;)V
    .registers 5

    const/16 p2, 0xa

    const-string p3, "activityStopped"

    invoke-direct {p0, p1, p2, p3}, Ladapter/activity/ActivityClientControllerAdapter;->reportOhLifecycle(Landroid/os/IBinder;ILjava/lang/String;)V

    return-void
.end method

.method public activityTopResumedStateLost()V
    .registers 1

    return-void
.end method

.method public checkActivityCallerContentUriPermission(Landroid/os/IBinder;Landroid/os/IBinder;Landroid/net/Uri;II)I
    .registers 6
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Landroid/os/RemoteException;
        }
    .end annotation

    const/4 p0, -0x1

    return p0
.end method

.method public clearOverrideActivityTransition(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public convertFromTranslucent(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x0

    return p0
.end method

.method public convertToTranslucent(Landroid/os/IBinder;Landroid/os/Bundle;)Z
    .registers 3

    const/4 p0, 0x0

    return p0
.end method

.method public dismissKeyguard(Landroid/os/IBinder;Lcom/android/internal/policy/IKeyguardDismissCallback;Ljava/lang/CharSequence;)V
    .registers 4

    return-void
.end method

.method public enableTaskLocaleOverride(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public enterPictureInPictureMode(Landroid/os/IBinder;Landroid/app/PictureInPictureParams;)Z
    .registers 3

    const/4 p0, 0x0

    return p0
.end method

.method public finishActivity(Landroid/os/IBinder;ILandroid/content/Intent;I)Z
    .registers 9

    const-string p0, "OH_ACCAdapter"

    const-string p3, "finishActivity: OH TerminateAbility(token=0x"

    :try_start_4
    invoke-static {p1}, Ladapter/core/OhTokenRegistry;->findOhToken(Landroid/os/IBinder;)Ljava/lang/Long;

    move-result-object p4

    if-eqz p4, :cond_44

    invoke-virtual {p4}, Ljava/lang/Long;->longValue()J

    move-result-wide v0

    const-wide/16 v2, 0x0

    cmp-long v0, v0, v2

    if-eqz v0, :cond_44

    invoke-virtual {p4}, Ljava/lang/Long;->longValue()J

    move-result-wide v0

    invoke-static {v0, v1, p2}, Ladapter/activity/ActivityClientControllerAdapter;->nativeTerminateAbilityByTokenAddr(JI)I

    move-result p1

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0, p3}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p4}, Ljava/lang/Long;->longValue()J

    move-result-wide p3

    invoke-static {p3, p4}, Ljava/lang/Long;->toHexString(J)Ljava/lang/String;

    move-result-object p3

    invoke-virtual {v0, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string p3, ", code="

    invoke-virtual {v0, p3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0, p2}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string p2, ") rc="

    invoke-virtual {v0, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p1

    invoke-static {p0, p1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_4e

    :cond_44
    invoke-static {p1}, Ladapter/activity/ActivityClientControllerAdapter;->scheduleLocalDestroy(Landroid/os/IBinder;)V
    :try_end_47
    .catchall {:try_start_4 .. :try_end_47} :catchall_48

    goto :goto_4e

    :catchall_48
    move-exception p1

    const-string p2, "finishActivity reverse callback failed"

    invoke-static {p0, p2, p1}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    :goto_4e
    const/4 p0, 0x1

    return p0
.end method

.method public finishActivityAffinity(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x1

    return p0
.end method

.method public finishSubActivity(Landroid/os/IBinder;Ljava/lang/String;I)V
    .registers 4

    return-void
.end method

.method public getActivityCallerPackage(Landroid/os/IBinder;Landroid/os/IBinder;)Ljava/lang/String;
    .registers 3
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Landroid/os/RemoteException;
        }
    .end annotation

    const/4 p0, 0x0

    return-object p0
.end method

.method public getActivityCallerUid(Landroid/os/IBinder;Landroid/os/IBinder;)I
    .registers 3
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Landroid/os/RemoteException;
        }
    .end annotation

    const/4 p0, -0x1

    return p0
.end method

.method public getActivityTokenBelow(Landroid/os/IBinder;)Landroid/os/IBinder;
    .registers 2

    const/4 p0, 0x0

    return-object p0
.end method

.method public getCallingActivity(Landroid/os/IBinder;)Landroid/content/ComponentName;
    .registers 2

    const/4 p0, 0x0

    return-object p0
.end method

.method public getCallingPackage(Landroid/os/IBinder;)Ljava/lang/String;
    .registers 2

    const/4 p0, 0x0

    return-object p0
.end method

.method public getDisplayId(Landroid/os/IBinder;)I
    .registers 2

    const/4 p0, 0x0

    return p0
.end method

.method public getLaunchedFromPackage(Landroid/os/IBinder;)Ljava/lang/String;
    .registers 2

    const/4 p0, 0x0

    return-object p0
.end method

.method public getLaunchedFromUid(Landroid/os/IBinder;)I
    .registers 2

    const/4 p0, 0x0

    return p0
.end method

.method public getRequestedOrientation(Landroid/os/IBinder;)I
    .registers 2

    const/4 p0, -0x1

    return p0
.end method

.method public getTaskConfiguration(Landroid/os/IBinder;)Landroid/content/res/Configuration;
    .registers 2

    const/4 p0, 0x0

    return-object p0
.end method

.method public getTaskForActivity(Landroid/os/IBinder;Z)I
    .registers 3

    const/4 p0, -0x1

    return p0
.end method

.method public invalidateHomeTaskSnapshot(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public isImmersive(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x0

    return p0
.end method

.method public isRequestedToLaunchInTaskFragment(Landroid/os/IBinder;Landroid/os/IBinder;)Z
    .registers 3

    const/4 p0, 0x0

    return p0
.end method

.method public isRootVoiceInteraction(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x0

    return p0
.end method

.method public isTopOfTask(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x1

    return p0
.end method

.method public moveActivityTaskToBack(Landroid/os/IBinder;Z)Z
    .registers 3

    const/4 p0, 0x0

    return p0
.end method

.method public navigateUpTo(Landroid/os/IBinder;Landroid/content/Intent;Ljava/lang/String;ILandroid/content/Intent;)Z
    .registers 6

    const/4 p0, 0x0

    return p0
.end method

.method public onBackPressed(Landroid/os/IBinder;Landroid/app/IRequestFinishCallback;)V
    .registers 3

    return-void
.end method

.method public overrideActivityTransition(Landroid/os/IBinder;ZIII)V
    .registers 6

    return-void
.end method

.method public overridePendingTransition(Landroid/os/IBinder;Ljava/lang/String;III)V
    .registers 6

    return-void
.end method

.method public registerRemoteAnimations(Landroid/os/IBinder;Landroid/view/RemoteAnimationDefinition;)V
    .registers 3

    return-void
.end method

.method public releaseActivityInstance(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x0

    return p0
.end method

.method public reportActivityFullyDrawn(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public reportSizeConfigurations(Landroid/os/IBinder;Landroid/window/SizeConfigurationBuckets;)V
    .registers 3

    return-void
.end method

.method public requestCompatCameraControl(Landroid/os/IBinder;ZZLandroid/app/ICompatCameraControlCallback;)V
    .registers 5

    return-void
.end method

.method public requestMultiwindowFullscreen(Landroid/os/IBinder;ILandroid/os/IRemoteCallback;)V
    .registers 4

    return-void
.end method

.method public setActivityRecordInputSinkEnabled(Landroid/os/IBinder;Z)V
    .registers 3
    .annotation system Ldalvik/annotation/Throws;
        value = {
            Landroid/os/RemoteException;
        }
    .end annotation

    new-instance p0, Ljava/lang/UnsupportedOperationException;

    const-string p1, "OpenHarmony activity input sink is not connected"

    invoke-direct {p0, p1}, Ljava/lang/UnsupportedOperationException;-><init>(Ljava/lang/String;)V

    throw p0
.end method

.method public setAllowCrossUidActivitySwitchFromBelow(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setForceSendResultForMediaProjection(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public setImmersive(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setInheritShowWhenLocked(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setPictureInPictureParams(Landroid/os/IBinder;Landroid/app/PictureInPictureParams;)V
    .registers 3

    return-void
.end method

.method public setRecentsScreenshotEnabled(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setRequestedOrientation(Landroid/os/IBinder;I)V
    .registers 3

    return-void
.end method

.method public setShouldDockBigOverlays(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setShowWhenLocked(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setTaskDescription(Landroid/os/IBinder;Landroid/app/ActivityManager$TaskDescription;)V
    .registers 3

    return-void
.end method

.method public setTurnScreenOn(Landroid/os/IBinder;Z)V
    .registers 3

    return-void
.end method

.method public setVrMode(Landroid/os/IBinder;ZLandroid/content/ComponentName;)I
    .registers 4

    const/4 p0, 0x0

    return p0
.end method

.method public shouldUpRecreateTask(Landroid/os/IBinder;Ljava/lang/String;)Z
    .registers 3

    const/4 p0, 0x0

    return p0
.end method

.method public showAssistFromActivity(Landroid/os/IBinder;Landroid/os/Bundle;)Z
    .registers 3

    const/4 p0, 0x0

    return p0
.end method

.method public showLockTaskEscapeMessage(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public splashScreenAttached(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public startLocalVoiceInteraction(Landroid/os/IBinder;Landroid/os/Bundle;)V
    .registers 3

    return-void
.end method

.method public startLockTaskModeByToken(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public stopLocalVoiceInteraction(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public stopLockTaskModeByToken(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public toggleFreeformWindowingMode(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public unregisterRemoteAnimations(Landroid/os/IBinder;)V
    .registers 2

    return-void
.end method

.method public willActivityBeVisible(Landroid/os/IBinder;)Z
    .registers 2

    const/4 p0, 0x1

    return p0
.end method
