.class public final Ladapter/activity/InputEventDeviceProjection;
.super Ljava/lang/Object;
.source "InputEventDeviceProjection.java"


# static fields
.field private static final TAG:Ljava/lang/String; = "OH_InputDeviceProjection"

.field private static volatile sDispatchMethod:Ljava/lang/reflect/Method; = null

.field private static volatile sMainHandler:Landroid/os/Handler; = null

.field private static volatile sTouchDeviceId:I = -0x80000000


# direct methods
.method static constructor <clinit>()V
    .registers 0

    return-void
.end method

.method private constructor <init>()V
    .registers 1

    .line 25
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method public static dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V
    .registers 7

    if-eqz p0, :cond_4c

    if-nez p2, :cond_5

    goto :goto_4c

    .line 137
    :cond_5
    invoke-static {}, Ladapter/activity/InputEventDeviceProjection;->resolveDispatchMethod()Ljava/lang/reflect/Method;

    move-result-object v0

    if-nez v0, :cond_c

    goto :goto_4c

    .line 141
    :cond_c
    invoke-static {p2}, Ladapter/activity/InputEventDeviceProjection;->projectDevice(Landroid/view/InputEvent;)Landroid/view/InputEvent;

    move-result-object p2

    .line 142
    invoke-static {}, Ladapter/activity/InputEventDeviceProjection;->getMainHandler()Landroid/os/Handler;

    move-result-object v1

    .line 143
    invoke-static {}, Landroid/os/Looper;->myLooper()Landroid/os/Looper;

    move-result-object v2

    invoke-virtual {v1}, Landroid/os/Handler;->getLooper()Landroid/os/Looper;

    move-result-object v3

    if-ne v2, v3, :cond_44

    .line 145
    :try_start_1e
    invoke-static {p1}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object p1

    const/4 v1, 0x2

    new-array v1, v1, [Ljava/lang/Object;

    const/4 v2, 0x0

    aput-object p1, v1, v2

    const/4 p1, 0x1

    aput-object p2, v1, p1

    invoke-virtual {v0, p0, v1}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    :try_end_2e
    .catchall {:try_start_1e .. :try_end_2e} :catchall_2f

    return-void

    :catchall_2f
    move-exception p0

    .line 147
    new-instance p1, Ljava/lang/StringBuilder;

    const-string p2, "inline dispatch failed: "

    invoke-direct {p1, p2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {p1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {p1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object p0

    const-string p1, "OH_InputDeviceProjection"

    invoke-static {p1, p0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    return-void

    .line 151
    :cond_44
    new-instance v2, Ladapter/activity/InputEventDeviceProjection$1;

    invoke-direct {v2, v0, p0, p1, p2}, Ladapter/activity/InputEventDeviceProjection$1;-><init>(Ljava/lang/reflect/Method;Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V

    invoke-virtual {v1, v2}, Landroid/os/Handler;->post(Ljava/lang/Runnable;)Z

    :cond_4c
    :goto_4c
    return-void
.end method

.method private static getMainHandler()Landroid/os/Handler;
    .registers 3

    .line 29
    sget-object v0, Ladapter/activity/InputEventDeviceProjection;->sMainHandler:Landroid/os/Handler;

    if-nez v0, :cond_1b

    .line 31
    const-class v1, Ladapter/activity/InputEventDeviceProjection;

    monitor-enter v1

    .line 32
    :try_start_7
    sget-object v0, Ladapter/activity/InputEventDeviceProjection;->sMainHandler:Landroid/os/Handler;

    if-nez v0, :cond_16

    .line 34
    new-instance v0, Landroid/os/Handler;

    invoke-static {}, Landroid/os/Looper;->getMainLooper()Landroid/os/Looper;

    move-result-object v2

    invoke-direct {v0, v2}, Landroid/os/Handler;-><init>(Landroid/os/Looper;)V

    .line 35
    sput-object v0, Ladapter/activity/InputEventDeviceProjection;->sMainHandler:Landroid/os/Handler;

    .line 37
    :cond_16
    monitor-exit v1

    return-object v0

    :catchall_18
    move-exception v0

    monitor-exit v1
    :try_end_1a
    .catchall {:try_start_7 .. :try_end_1a} :catchall_18

    throw v0

    :cond_1b
    return-object v0
.end method

.method private static projectDevice(Landroid/view/InputEvent;)Landroid/view/InputEvent;
    .registers 20

    move-object/from16 v0, p0

    .line 95
    const-string v1, "OH_InputDeviceProjection"

    .line 0
    const-string v2, "projected MotionEvent deviceId="

    .line 95
    instance-of v3, v0, Landroid/view/MotionEvent;

    if-nez v3, :cond_b

    return-object v0

    .line 98
    :cond_b
    move-object v3, v0

    check-cast v3, Landroid/view/MotionEvent;

    .line 100
    :try_start_e
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getDeviceId()I

    move-result v0

    const/16 v4, 0x1002

    if-eqz v0, :cond_23

    .line 102
    invoke-static {v0}, Landroid/view/InputDevice;->getDevice(I)Landroid/view/InputDevice;

    move-result-object v5

    if-eqz v5, :cond_23

    .line 104
    invoke-virtual {v5, v4}, Landroid/view/InputDevice;->supportsSource(I)Z

    move-result v5

    if-eqz v5, :cond_23

    goto :goto_30

    .line 108
    :cond_23
    invoke-virtual {v3, v4}, Landroid/view/MotionEvent;->isFromSource(I)Z

    move-result v4

    if-nez v4, :cond_2a

    goto :goto_30

    .line 111
    :cond_2a
    invoke-static {}, Ladapter/activity/InputEventDeviceProjection;->resolveTouchDeviceId()I

    move-result v17

    if-nez v17, :cond_31

    :goto_30
    return-object v3

    .line 116
    :cond_31
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getDownTime()J

    move-result-wide v5

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getEventTime()J

    move-result-wide v7

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getAction()I

    move-result v9

    .line 117
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getX()F

    move-result v10

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getY()F

    move-result v11

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getPressure()F

    move-result v12

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getSize()F

    move-result v13

    .line 118
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getMetaState()I

    move-result v14

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getXPrecision()F

    move-result v15

    invoke-virtual {v3}, Landroid/view/MotionEvent;->getYPrecision()F

    move-result v16

    .line 119
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getEdgeFlags()I

    move-result v18

    .line 115
    invoke-static/range {v5 .. v18}, Landroid/view/MotionEvent;->obtain(JJIFFFFIFFII)Landroid/view/MotionEvent;

    move-result-object v4

    move/from16 v5, v17

    .line 120
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getSource()I

    move-result v6

    invoke-virtual {v4, v6}, Landroid/view/MotionEvent;->setSource(I)V

    .line 121
    new-instance v6, Ljava/lang/StringBuilder;

    invoke-direct {v6, v2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v6, v0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v0, "->"

    invoke-virtual {v6, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v6, v5}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    const-string v0, " source=0x"

    invoke-virtual {v6, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    .line 123
    invoke-virtual {v3}, Landroid/view/MotionEvent;->getSource()I

    move-result v0

    invoke-static {v0}, Ljava/lang/Integer;->toHexString(I)Ljava/lang/String;

    move-result-object v0

    invoke-virtual {v6, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    .line 121
    invoke-static {v1, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_91
    .catchall {:try_start_e .. :try_end_91} :catchall_92

    return-object v4

    :catchall_92
    move-exception v0

    .line 126
    new-instance v2, Ljava/lang/StringBuilder;

    const-string v4, "MotionEvent projection failed: "

    invoke-direct {v2, v4}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v1, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    return-object v3
.end method

.method private static resolveDispatchMethod()Ljava/lang/reflect/Method;
    .registers 8

    .line 43
    const-string v0, "dispatch method lookup failed: "

    sget-object v1, Ladapter/activity/InputEventDeviceProjection;->sDispatchMethod:Ljava/lang/reflect/Method;

    if-nez v1, :cond_3f

    .line 45
    const-class v2, Ladapter/activity/InputEventDeviceProjection;

    monitor-enter v2

    .line 46
    :try_start_9
    sget-object v1, Ladapter/activity/InputEventDeviceProjection;->sDispatchMethod:Ljava/lang/reflect/Method;
    :try_end_b
    .catchall {:try_start_9 .. :try_end_b} :catchall_3c

    if-nez v1, :cond_3a

    .line 49
    :try_start_d
    const-class v3, Landroid/view/InputEventReceiver;

    const-string v4, "dispatchInputEvent"

    const/4 v5, 0x2

    new-array v5, v5, [Ljava/lang/Class;

    sget-object v6, Ljava/lang/Integer;->TYPE:Ljava/lang/Class;

    const/4 v7, 0x0

    aput-object v6, v5, v7

    const-class v6, Landroid/view/InputEvent;

    const/4 v7, 0x1

    aput-object v6, v5, v7

    invoke-virtual {v3, v4, v5}, Ljava/lang/Class;->getDeclaredMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;

    move-result-object v1

    .line 51
    invoke-virtual {v1, v7}, Ljava/lang/reflect/Method;->setAccessible(Z)V

    .line 52
    sput-object v1, Ladapter/activity/InputEventDeviceProjection;->sDispatchMethod:Ljava/lang/reflect/Method;
    :try_end_27
    .catchall {:try_start_d .. :try_end_27} :catchall_28

    goto :goto_3a

    :catchall_28
    move-exception v3

    .line 54
    :try_start_29
    const-string v4, "OH_InputDeviceProjection"

    new-instance v5, Ljava/lang/StringBuilder;

    invoke-direct {v5, v0}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v5, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v5}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v4, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I

    .line 57
    :cond_3a
    :goto_3a
    monitor-exit v2

    return-object v1

    :catchall_3c
    move-exception v0

    monitor-exit v2
    :try_end_3e
    .catchall {:try_start_29 .. :try_end_3e} :catchall_3c

    throw v0

    :cond_3f
    return-object v1
.end method

.method private static resolveTouchDeviceId()I
    .registers 8

    .line 63
    sget v0, Ladapter/activity/InputEventDeviceProjection;->sTouchDeviceId:I

    const/high16 v1, -0x80000000

    if-eq v0, v1, :cond_7

    return v0

    .line 67
    :cond_7
    const-class v0, Ladapter/activity/InputEventDeviceProjection;

    monitor-enter v0

    .line 68
    :try_start_a
    sget v2, Ladapter/activity/InputEventDeviceProjection;->sTouchDeviceId:I

    if-eq v2, v1, :cond_10

    .line 70
    monitor-exit v0
    :try_end_f
    .catchall {:try_start_a .. :try_end_f} :catchall_61

    return v2

    :cond_10
    const/4 v1, 0x0

    .line 74
    :try_start_11
    invoke-static {}, Landroid/view/InputDevice;->getDeviceIds()[I

    move-result-object v2

    if-eqz v2, :cond_47

    .line 76
    array-length v3, v2

    const/4 v4, 0x0

    :goto_19
    if-ge v4, v3, :cond_47

    aget v5, v2, v4

    .line 77
    invoke-static {v5}, Landroid/view/InputDevice;->getDevice(I)Landroid/view/InputDevice;

    move-result-object v6

    if-eqz v6, :cond_2d

    const/16 v7, 0x1002

    .line 79
    invoke-virtual {v6, v7}, Landroid/view/InputDevice;->supportsSource(I)Z

    move-result v6
    :try_end_29
    .catchall {:try_start_11 .. :try_end_29} :catchall_30

    if-eqz v6, :cond_2d

    move v1, v5

    goto :goto_47

    :cond_2d
    add-int/lit8 v4, v4, 0x1

    goto :goto_19

    :catchall_30
    move-exception v2

    .line 86
    :try_start_31
    const-string v3, "OH_InputDeviceProjection"

    new-instance v4, Ljava/lang/StringBuilder;

    invoke-direct {v4}, Ljava/lang/StringBuilder;-><init>()V

    const-string v5, "touch device lookup failed: "

    invoke-virtual {v4, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v4, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v4}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-static {v3, v2}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    .line 88
    :cond_47
    :goto_47
    sput v1, Ladapter/activity/InputEventDeviceProjection;->sTouchDeviceId:I

    .line 89
    const-string v2, "OH_InputDeviceProjection"

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    const-string v4, "touch device projection resolved id="

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v3, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-static {v2, v3}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 90
    monitor-exit v0

    return v1

    :catchall_61
    move-exception v1

    .line 91
    monitor-exit v0
    :try_end_63
    .catchall {:try_start_31 .. :try_end_63} :catchall_61

    throw v1
.end method
