.class Ladapter/activity/InputEventDeviceProjection$1;
.super Ljava/lang/Object;
.source "InputEventDeviceProjection.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Ladapter/activity/InputEventDeviceProjection;->dispatchOnMainThread(Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field final synthetic val$method:Ljava/lang/reflect/Method;

.field final synthetic val$projected:Landroid/view/InputEvent;

.field final synthetic val$receiver:Landroid/view/InputEventReceiver;

.field final synthetic val$seq:I


# direct methods
.method constructor <init>(Ljava/lang/reflect/Method;Landroid/view/InputEventReceiver;ILandroid/view/InputEvent;)V
    .registers 5
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "()V"
        }
    .end annotation

    .line 151
    iput-object p1, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$method:Ljava/lang/reflect/Method;

    iput-object p2, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$receiver:Landroid/view/InputEventReceiver;

    iput p3, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$seq:I

    iput-object p4, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$projected:Landroid/view/InputEvent;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .registers 7

    .line 155
    :try_start_0
    iget-object v0, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$method:Ljava/lang/reflect/Method;

    iget-object v1, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$receiver:Landroid/view/InputEventReceiver;

    iget v2, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$seq:I

    invoke-static {v2}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;

    move-result-object v2

    iget-object v3, p0, Ladapter/activity/InputEventDeviceProjection$1;->val$projected:Landroid/view/InputEvent;

    const/4 v4, 0x2

    new-array v4, v4, [Ljava/lang/Object;

    const/4 v5, 0x0

    aput-object v2, v4, v5

    const/4 v2, 0x1

    aput-object v3, v4, v2

    invoke-virtual {v0, v1, v4}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    :try_end_18
    .catchall {:try_start_0 .. :try_end_18} :catchall_19

    return-void

    :catchall_19
    move-exception v0

    .line 157
    new-instance v1, Ljava/lang/StringBuilder;

    const-string v2, "posted dispatch failed: "

    invoke-direct {v1, v2}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/Object;)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    const-string v1, "OH_InputDeviceProjection"

    invoke-static {v1, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;)I

    return-void
.end method
