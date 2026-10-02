.class public final Lcom/github/libretube/LibreTubeApp;
.super Landroid/app/Application;
.source "r8-map-id-ef56c544540bd8b5be9c10a121da3d4d73663697faa722ec8e9a285c9904a322"


# static fields
.field public static instance:Lcom/github/libretube/LibreTubeApp;


# direct methods
.method public constructor <init>()V
    .registers 1

    .line 1
    invoke-direct {p0}, Landroid/app/Application;-><init>()V

    .line 2
    .line 3
    .line 4
    return-void
.end method


# virtual methods
.method public final onCreate()V
    .registers 13

    .line 1
    invoke-super {p0}, Landroid/app/Application;->onCreate()V

    .line 2
    .line 3
    .line 4
    sput-object p0, Lcom/github/libretube/LibreTubeApp;->instance:Lcom/github/libretube/LibreTubeApp;

    .line 5
    .line 6
    new-instance v0, Landroidx/core/app/NotificationChannelCompat;

    .line 7
    .line 8
    const-string v1, "playlist_download_enqueue"

    .line 9
    .line 10
    const/4 v2, 0x2

    .line 11
    invoke-direct {v0, v1, v2}, Landroidx/core/app/NotificationChannelCompat;-><init>(Ljava/lang/String;I)V

    .line 12
    .line 13
    .line 14
    const v1, 0x7f1300f1

    .line 15
    .line 16
    .line 17
    invoke-virtual {p0, v1}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 18
    .line 19
    .line 20
    move-result-object v1

    .line 21
    iput-object v1, v0, Landroidx/core/app/NotificationChannelCompat;->mName:Ljava/lang/String;

    .line 22
    .line 23
    const v1, 0x7f130102

    .line 24
    .line 25
    .line 26
    invoke-virtual {p0, v1}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 27
    .line 28
    .line 29
    move-result-object v1

    .line 30
    iput-object v1, v0, Landroidx/core/app/NotificationChannelCompat;->mDescription:Ljava/lang/String;

    .line 31
    .line 32
    new-instance v1, Landroidx/core/app/NotificationChannelCompat;

    .line 33
    .line 34
    const-string v3, "download_service"

    .line 35
    .line 36
    invoke-direct {v1, v3, v2}, Landroidx/core/app/NotificationChannelCompat;-><init>(Ljava/lang/String;I)V

    .line 37
    .line 38
    .line 39
    const v3, 0x7f1300ee

    .line 40
    .line 41
    .line 42
    invoke-virtual {p0, v3}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 43
    .line 44
    .line 45
    move-result-object v3

    .line 46
    iput-object v3, v1, Landroidx/core/app/NotificationChannelCompat;->mName:Ljava/lang/String;

    .line 47
    .line 48
    const v3, 0x7f1300ed

    .line 49
    .line 50
    .line 51
    invoke-virtual {p0, v3}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 52
    .line 53
    .line 54
    move-result-object v3

    .line 55
    iput-object v3, v1, Landroidx/core/app/NotificationChannelCompat;->mDescription:Ljava/lang/String;

    .line 56
    .line 57
    new-instance v3, Landroidx/core/app/NotificationChannelCompat;

    .line 58
    .line 59
    const-string v4, "player_mode"

    .line 60
    .line 61
    invoke-direct {v3, v4, v2}, Landroidx/core/app/NotificationChannelCompat;-><init>(Ljava/lang/String;I)V

    .line 62
    .line 63
    .line 64
    const v4, 0x7f130280

    .line 65
    .line 66
    .line 67
    invoke-virtual {p0, v4}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 68
    .line 69
    .line 70
    move-result-object v4

    .line 71
    iput-object v4, v3, Landroidx/core/app/NotificationChannelCompat;->mName:Ljava/lang/String;

    .line 72
    .line 73
    const v4, 0x7f13027f

    .line 74
    .line 75
    .line 76
    invoke-virtual {p0, v4}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 77
    .line 78
    .line 79
    move-result-object v4

    .line 80
    iput-object v4, v3, Landroidx/core/app/NotificationChannelCompat;->mDescription:Ljava/lang/String;

    .line 81
    .line 82
    new-instance v4, Landroidx/core/app/NotificationChannelCompat;

    .line 83
    .line 84
    const-string v5, "notification_worker"

    .line 85
    .line 86
    const/4 v6, 0x3

    .line 87
    invoke-direct {v4, v5, v6}, Landroidx/core/app/NotificationChannelCompat;-><init>(Ljava/lang/String;I)V

    .line 88
    .line 89
    .line 90
    const v5, 0x7f130293

    .line 91
    .line 92
    .line 93
    invoke-virtual {p0, v5}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 94
    .line 95
    .line 96
    move-result-object v5

    .line 97
    iput-object v5, v4, Landroidx/core/app/NotificationChannelCompat;->mName:Ljava/lang/String;

    .line 98
    .line 99
    const v5, 0x7f130292

    .line 100
    .line 101
    .line 102
    invoke-virtual {p0, v5}, Landroid/content/Context;->getString(I)Ljava/lang/String;

    .line 103
    .line 104
    .line 105
    move-result-object v5

    .line 106
    iput-object v5, v4, Landroidx/core/app/NotificationChannelCompat;->mDescription:Ljava/lang/String;

    .line 107
    .line 108
    new-instance v5, Landroidx/core/app/NotificationManagerCompat;

    .line 109
    .line 110
    invoke-direct {v5, p0}, Landroidx/core/app/NotificationManagerCompat;-><init>(Landroid/content/Context;)V

    .line 111
    .line 112
    .line 113
    filled-new-array {v0, v1, v4, v3}, [Landroidx/core/app/NotificationChannelCompat;

    .line 114
    .line 115
    .line 116
    move-result-object v0

    .line 117
    invoke-static {v0}, Lkotlin/ResultKt;->listOf([Ljava/lang/Object;)Ljava/util/List;

    .line 118
    .line 119
    .line 120
    move-result-object v0

    .line 121
    invoke-interface {v0}, Ljava/util/List;->isEmpty()Z

    .line 122
    .line 123
    .line 124
    move-result v1

    .line 125
    const/4 v3, 0x0

    .line 126
    const/4 v4, 0x0

    .line 127
    if-nez v1, :cond_cc

    .line 128
    .line 129
    new-instance v1, Ljava/util/ArrayList;

    .line 130
    .line 131
    invoke-interface {v0}, Ljava/util/List;->size()I

    .line 132
    .line 133
    .line 134
    move-result v7

    .line 135
    invoke-direct {v1, v7}, Ljava/util/ArrayList;-><init>(I)V

    .line 136
    .line 137
    .line 138
    invoke-interface {v0}, Ljava/util/List;->iterator()Ljava/util/Iterator;

    .line 139
    .line 140
    .line 141
    move-result-object v0

    .line 142
    :goto_8d
    invoke-interface {v0}, Ljava/util/Iterator;->hasNext()Z

    .line 143
    .line 144
    .line 145
    move-result v7

    .line 146
    if-eqz v7, :cond_c7

    .line 147
    .line 148
    invoke-interface {v0}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    .line 149
    .line 150
    .line 151
    move-result-object v7

    .line 152
    check-cast v7, Landroidx/core/app/NotificationChannelCompat;

    .line 153
    .line 154
    iget-object v8, v7, Landroidx/core/app/NotificationChannelCompat;->mId:Ljava/lang/String;

    .line 155
    .line 156
    iget-object v9, v7, Landroidx/core/app/NotificationChannelCompat;->mName:Ljava/lang/String;

    .line 157
    .line 158
    iget v10, v7, Landroidx/core/app/NotificationChannelCompat;->mImportance:I

    .line 159
    .line 160
    new-instance v11, Landroid/app/NotificationChannel;

    .line 161
    .line 162
    invoke-direct {v11, v8, v9, v10}, Landroid/app/NotificationChannel;-><init>(Ljava/lang/String;Ljava/lang/CharSequence;I)V

    .line 163
    .line 164
    .line 165
    iget-object v8, v7, Landroidx/core/app/NotificationChannelCompat;->mDescription:Ljava/lang/String;

    .line 166
    .line 167
    invoke-virtual {v11, v8}, Landroid/app/NotificationChannel;->setDescription(Ljava/lang/String;)V

    .line 168
    .line 169
    .line 170
    invoke-virtual {v11, v4}, Landroid/app/NotificationChannel;->setGroup(Ljava/lang/String;)V

    .line 171
    .line 172
    .line 173
    const/4 v8, 0x1

    .line 174
    invoke-virtual {v11, v8}, Landroid/app/NotificationChannel;->setShowBadge(Z)V

    .line 175
    .line 176
    .line 177
    iget-object v8, v7, Landroidx/core/app/NotificationChannelCompat;->mSound:Landroid/net/Uri;

    .line 178
    .line 179
    iget-object v7, v7, Landroidx/core/app/NotificationChannelCompat;->mAudioAttributes:Landroid/media/AudioAttributes;

    .line 180
    .line 181
    invoke-virtual {v11, v8, v7}, Landroid/app/NotificationChannel;->setSound(Landroid/net/Uri;Landroid/media/AudioAttributes;)V

    .line 182
    .line 183
    .line 184
    invoke-virtual {v11, v3}, Landroid/app/NotificationChannel;->enableLights(Z)V

    .line 185
    .line 186
    .line 187
    invoke-virtual {v11, v3}, Landroid/app/NotificationChannel;->setLightColor(I)V

    .line 188
    .line 189
    .line 190
    invoke-virtual {v11, v4}, Landroid/app/NotificationChannel;->setVibrationPattern([J)V

    .line 191
    .line 192
    .line 193
    invoke-virtual {v11, v3}, Landroid/app/NotificationChannel;->enableVibration(Z)V

    .line 194
    .line 195
    .line 196
    invoke-virtual {v1, v11}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    .line 197
    .line 198
    .line 199
    goto :goto_8d

    .line 200
    :cond_c7
    iget-object v0, v5, Landroidx/core/app/NotificationManagerCompat;->mNotificationManager:Landroid/app/NotificationManager;

    .line 201
    .line 202
    invoke-virtual {v0, v1}, Landroid/app/NotificationManager;->createNotificationChannels(Ljava/util/List;)V

    .line 203
    .line 204
    .line 205
    :cond_cc
    sget-object v0, Lcom/github/libretube/helpers/PreferenceHelper;->TAG:Ljava/lang/String;

    .line 206
    .line 207
    invoke-virtual {p0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;

    .line 208
    .line 209
    .line 210
    move-result-object v0

    .line 211
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    .line 212
    .line 213
    .line 214
    new-instance v1, Ljava/lang/StringBuilder;

    .line 215
    .line 216
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    .line 217
    .line 218
    .line 219
    invoke-virtual {v0}, Landroid/content/Context;->getPackageName()Ljava/lang/String;

    .line 220
    .line 221
    .line 222
    move-result-object v5

    .line 223
    invoke-virtual {v1, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    .line 224
    .line 225
    .line 226
    const-string v5, "_preferences"

    .line 227
    .line 228
    invoke-virtual {v1, v5}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    .line 229
    .line 230
    .line 231
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    .line 232
    .line 233
    .line 234
    move-result-object v1

    .line 235
    invoke-virtual {v0, v1, v3}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    .line 236
    .line 237
    .line 238
    move-result-object v1

    .line 239
    invoke-virtual {v1}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    .line 240
    .line 241
    .line 242
    sput-object v1, Lcom/github/libretube/helpers/PreferenceHelper;->settings:Landroid/content/SharedPreferences;

    .line 243
    .line 244
    const-string v1, "auth"

    .line 245
    .line 246
    invoke-virtual {v0, v1, v3}, Landroid/content/Context;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    .line 247
    .line 248
    .line 249
    move-result-object v0

    .line 250
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    .line 251
    .line 252
    .line 253
    sput-object v0, Lcom/github/libretube/helpers/PreferenceHelper;->authSettings:Landroid/content/SharedPreferences;

    .line 254
    .line 255
    const-string v0, "PREFERENCE_VERSION"

    .line 256
    .line 257
    invoke-static {v3, v0}, Lcom/github/libretube/helpers/PreferenceHelper;->getInt(ILjava/lang/String;)I

    .line 258
    .line 259
    .line 260
    move-result v1

    .line 261
    :goto_104
    sget-object v5, Lcom/github/libretube/helpers/PreferenceHelper;->MIGRATIONS:[Lokhttp3/internal/http2/Huffman$Node;

    .line 262
    .line 263
    array-length v7, v5

    .line 264
    if-ge v1, v7, :cond_14b

    .line 265
    .line 266
    add-int/lit8 v7, v1, 0x1

    .line 267
    .line 268
    array-length v8, v5

    .line 269
    move v9, v3

    .line 270
    :goto_10d
    if-ge v9, v8, :cond_121

    .line 271
    .line 272
    aget-object v10, v5, v9

    .line 273
    .line 274
    invoke-virtual {v10}, Lokhttp3/internal/http2/Huffman$Node;->getFromVersion()I

    .line 275
    .line 276
    .line 277
    move-result v11

    .line 278
    if-ne v11, v1, :cond_11e

    .line 279
    .line 280
    invoke-virtual {v10}, Lokhttp3/internal/http2/Huffman$Node;->getToVersion()I

    .line 281
    .line 282
    .line 283
    move-result v11

    .line 284
    if-ne v11, v7, :cond_11e

    .line 285
    .line 286
    goto :goto_122

    .line 287
    :cond_11e
    add-int/lit8 v9, v9, 0x1

    .line 288
    .line 289
    goto :goto_10d

    .line 290
    :cond_121
    move-object v10, v4

    .line 291
    :goto_122
    sget-object v5, Lcom/github/libretube/helpers/PreferenceHelper;->TAG:Ljava/lang/String;

    .line 292
    .line 293
    new-instance v8, Ljava/lang/StringBuilder;

    .line 294
    .line 295
    const-string v9, "Performing migration from "

    .line 296
    .line 297
    invoke-direct {v8, v9}, Ljava/lang/StringBuilder;-><init>(Ljava/lang/String;)V

    .line 298
    .line 299
    .line 300
    invoke-virtual {v8, v1}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    .line 301
    .line 302
    .line 303
    const-string v1, " to "

    .line 304
    .line 305
    invoke-virtual {v8, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    .line 306
    .line 307
    .line 308
    invoke-virtual {v8, v7}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    .line 309
    .line 310
    .line 311
    invoke-virtual {v8}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    .line 312
    .line 313
    .line 314
    move-result-object v1

    .line 315
    invoke-static {v5, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 316
    .line 317
    .line 318
    if-eqz v10, :cond_146

    .line 319
    .line 320
    invoke-virtual {v10}, Lokhttp3/internal/http2/Huffman$Node;->getOnMigration()Lkotlin/jvm/functions/Function0;

    .line 321
    .line 322
    .line 323
    move-result-object v1

    .line 324
    invoke-interface {v1}, Lkotlin/jvm/functions/Function0;->invoke()Ljava/lang/Object;

    .line 325
    .line 326
    .line 327
    :cond_146
    invoke-static {v7, v0}, Lcom/github/libretube/helpers/PreferenceHelper;->putInt(ILjava/lang/String;)V

    .line 328
    .line 329
    .line 330
    move v1, v7

    .line 331
    goto :goto_104

    .line 332
    :cond_14b
    new-instance v0, Lokhttp3/OkHttpClient;

    .line 333
    .line 334
    invoke-direct {v0}, Lokhttp3/OkHttpClient;-><init>()V

    .line 335
    .line 336
    .line 337
    invoke-virtual {v0}, Lokhttp3/OkHttpClient;->newBuilder()Lokhttp3/OkHttpClient$Builder;

    .line 338
    .line 339
    .line 340
    move-result-object v0

    .line 341
    new-instance v1, Lcoil3/ImageLoader$Builder;

    .line 342
    .line 343
    invoke-direct {v1, p0}, Lcoil3/ImageLoader$Builder;-><init>(Landroid/content/Context;)V

    .line 344
    .line 345
    .line 346
    invoke-static {v1}, Lcoil3/request/ImageRequestsKt;->crossfade(Lcoil3/ImageLoader$Builder;)V

    .line 347
    .line 348
    .line 349
    new-instance v3, Lcoil3/ComponentRegistry$Builder;

    .line 350
    .line 351
    invoke-direct {v3}, Lcoil3/ComponentRegistry$Builder;-><init>()V

    .line 352
    .line 353
    .line 354
    new-instance v5, Lokhttp3/OkHttpClient;

    .line 355
    .line 356
    invoke-direct {v5, v0}, Lokhttp3/OkHttpClient;-><init>(Lokhttp3/OkHttpClient$Builder;)V

    .line 357
    .line 358
    .line 359
    invoke-static {v5}, Lcoil3/util/LifecyclesKt;->factory(Lokhttp3/OkHttpClient;)Lcoil3/network/NetworkFetcher$Factory;

    .line 360
    .line 361
    .line 362
    move-result-object v0

    .line 363
    const-class v5, Lcoil3/Uri;

    .line 364
    .line 365
    invoke-static {v5}, Lkotlin/jvm/internal/Reflection;->getOrCreateKotlinClass(Ljava/lang/Class;)Lkotlin/jvm/internal/ClassReference;

    .line 366
    .line 367
    .line 368
    move-result-object v5

    .line 369
    invoke-virtual {v3, v0, v5}, Lcoil3/ComponentRegistry$Builder;->add(Lcoil3/fetch/Fetcher$Factory;Lkotlin/jvm/internal/ClassReference;)V

    .line 370
    .line 371
    .line 372
    invoke-virtual {v3}, Lcoil3/ComponentRegistry$Builder;->build()Lcoil3/ComponentRegistry;

    .line 373
    .line 374
    .line 375
    move-result-object v0

    .line 376
    invoke-virtual {v1, v0}, Lcoil3/ImageLoader$Builder;->components(Lcoil3/ComponentRegistry;)V

    .line 377
    .line 378
    .line 379
    invoke-virtual {v1}, Lcoil3/ImageLoader$Builder;->diskCachePolicy()V

    .line 380
    .line 381
    .line 382
    invoke-virtual {v1}, Lcoil3/ImageLoader$Builder;->memoryCachePolicy()V

    .line 383
    .line 384
    .line 385
    const-class v0, Landroid/os/storage/StorageManager;

    .line 386
    .line 387
    invoke-virtual {p0, v0}, Landroid/content/Context;->getSystemService(Ljava/lang/Class;)Ljava/lang/Object;

    .line 388
    .line 389
    .line 390
    move-result-object v0

    .line 391
    invoke-virtual {v0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;

    .line 392
    .line 393
    .line 394
    check-cast v0, Landroid/os/storage/StorageManager;

    .line 395
    .line 396
    invoke-static {p0}, Lcom/github/libretube/helpers/ImageHelper;->getCoilFile(Lcom/github/libretube/LibreTubeApp;)Ljava/io/File;

    .line 397
    .line 398
    .line 399
    move-result-object v3

    .line 400
    invoke-virtual {v0, v3}, Landroid/os/storage/StorageManager;->getUuidForPath(Ljava/io/File;)Ljava/util/UUID;

    .line 401
    .line 402
    .line 403
    move-result-object v3

    .line 404
    invoke-virtual {v0, v3}, Landroid/os/storage/StorageManager;->getCacheQuotaBytes(Ljava/util/UUID;)J

    .line 405
    .line 406
    .line 407
    move-result-wide v7

    .line 408
    new-instance v0, Lcoil3/disk/DiskCache$Builder;

    .line 409
    .line 410
    invoke-direct {v0}, Lcoil3/disk/DiskCache$Builder;-><init>()V

    .line 411
    .line 412
    .line 413
    invoke-static {p0}, Lcom/github/libretube/helpers/ImageHelper;->getCoilFile(Lcom/github/libretube/LibreTubeApp;)Ljava/io/File;

    .line 414
    .line 415
    .line 416
    move-result-object v3

    .line 417
    invoke-static {v0, v3}, Landroidx/work/TracerKt;->directory(Lcoil3/disk/DiskCache$Builder;Ljava/io/File;)V

    .line 418
    .line 419
    .line 420
    invoke-virtual {v0, v7, v8}, Lcoil3/disk/DiskCache$Builder;->maxSizeBytes(J)V

    .line 421
    .line 422
    .line 423
    invoke-virtual {v0}, Lcoil3/disk/DiskCache$Builder;->build()Lcoil3/disk/RealDiskCache;

    .line 424
    .line 425
    .line 426
    move-result-object v0

    .line 427
    invoke-virtual {v1, v0}, Lcoil3/ImageLoader$Builder;->diskCache(Lcoil3/disk/RealDiskCache;)V

    .line 428
    .line 429
    .line 430
    invoke-virtual {v1}, Lcoil3/ImageLoader$Builder;->build()Lcoil3/RealImageLoader;

    .line 431
    .line 432
    .line 433
    move-result-object v0

    .line 434
    sput-object v0, Lcom/github/libretube/helpers/ImageHelper;->imageLoader:Lcoil3/RealImageLoader;

    .line 435
    .line 436
    sget-object v0, Landroidx/work/ExistingPeriodicWorkPolicy;->KEEP:Landroidx/work/ExistingPeriodicWorkPolicy;

    .line 437
    .line 438
    invoke-static {p0, v0}, Lkotlin/ResultKt;->enqueueWork(Landroid/content/Context;Landroidx/work/ExistingPeriodicWorkPolicy;)V

    .line 439
    .line 440
    .line 441
    sget-object v0, Lkotlinx/coroutines/Dispatchers;->Default:Lkotlinx/coroutines/scheduling/DefaultScheduler;

    .line 442
    .line 443
    sget-object v0, Lkotlinx/coroutines/scheduling/DefaultIoScheduler;->INSTANCE:Lkotlinx/coroutines/scheduling/DefaultIoScheduler;

    .line 444
    .line 445
    invoke-static {v0}, Lkotlinx/coroutines/JobKt;->CoroutineScope(Lkotlin/coroutines/CoroutineContext;)Lkotlinx/coroutines/internal/ContextScope;

    .line 446
    .line 447
    .line 448
    move-result-object v1

    .line 449
    new-instance v3, Landroidx/work/CoroutineWorker$startWork$1;

    .line 450
    .line 451
    invoke-direct {v3, v2, v4}, Landroidx/work/CoroutineWorker$startWork$1;-><init>(ILkotlin/coroutines/Continuation;)V

    .line 452
    .line 453
    .line 454
    invoke-static {v1, v4, v4, v3, v6}, Lkotlinx/coroutines/JobKt;->launch$default(Lkotlinx/coroutines/CoroutineScope;Lkotlin/coroutines/CoroutineContext;Lkotlinx/coroutines/CoroutineStart;Lkotlin/jvm/functions/Function2;I)Lkotlinx/coroutines/StandaloneCoroutine;

    .line 455
    .line 456
    .line 457
    invoke-static {}, Ljava/lang/Thread;->getDefaultUncaughtExceptionHandler()Ljava/lang/Thread$UncaughtExceptionHandler;

    .line 458
    .line 459
    .line 460
    move-result-object v1

    .line 461
    new-instance v2, Lcom/github/libretube/util/ExceptionHandler;

    .line 462
    .line 463
    invoke-direct {v2, v1}, Lcom/github/libretube/util/ExceptionHandler;-><init>(Ljava/lang/Thread$UncaughtExceptionHandler;)V

    .line 464
    .line 465
    .line 466
    invoke-static {v2}, Ljava/lang/Thread;->setDefaultUncaughtExceptionHandler(Ljava/lang/Thread$UncaughtExceptionHandler;)V

    .line 467
    .line 468
    .line 469
    invoke-static {v0}, Lkotlinx/coroutines/JobKt;->CoroutineScope(Lkotlin/coroutines/CoroutineContext;)Lkotlinx/coroutines/internal/ContextScope;

    .line 470
    .line 471
    .line 472
    move-result-object v0

    .line 473
    new-instance v1, Lcoil3/disk/DiskLruCache$launchCleanup$1;

    .line 474
    .line 475
    const/4 v2, 0x4

    .line 476
    invoke-direct {v1, v2, p0, v4}, Lcoil3/disk/DiskLruCache$launchCleanup$1;-><init>(ILjava/lang/Object;Lkotlin/coroutines/Continuation;)V

    .line 477
    .line 478
    .line 479
    invoke-static {v0, v4, v4, v1, v6}, Lkotlinx/coroutines/JobKt;->launch$default(Lkotlinx/coroutines/CoroutineScope;Lkotlin/coroutines/CoroutineContext;Lkotlinx/coroutines/CoroutineStart;Lkotlin/jvm/functions/Function2;I)Lkotlinx/coroutines/StandaloneCoroutine;

    .line 480
    .line 481
    .line 482
    invoke-static {}, Lcom/github/libretube/helpers/NewPipeExtractorInstance;->init()V

    .line 483
    .line 484
    .line 485
    return-void
.end method

