/*
 * PlayVideoActivity.java
 *
 * L12 视频/媒体插件楼层的最小验证场景（2026-07-10 新增）。
 *
 * 目的：用尽量小的、标准的 android.media.MediaPlayer + SurfaceView 调用序列，
 * 精确命中 adapter 新增的 register_android_media_MediaPlayer JNI 桩实现
 * （见 framework/android-runtime/src/android_media_MediaPlayer.cpp 文件头的
 * 完整证据链和能力边界说明）。
 *
 * 这是纯标准 Android 代码 —— 不 import 任何 adapter.* 类，不检测 OH 环境，
 * 与 HelloWorld 项目"APK 透明适配"的核心约束一致（同目录 MainActivity.java
 * 的注释）。
 *
 * 验证的调用序列（对应 android_media_MediaPlayer.cpp 里实现的桩方法）：
 *   1. new MediaPlayer()                      -> native_setup
 *   2. mp.setOnPreparedListener/OnErrorListener
 *   3. mp.setDataSource(AssetFileDescriptor)   -> _setDataSource(fd,off,len)
 *   4. surfaceCreated -> mp.setSurface(holder.getSurface())
 *                                              -> _setVideoSurface(Surface)
 *   5. mp.prepareAsync()                       -> _prepareAsync(Parcel)
 *   6. onPrepared 回调触发 -> mp.start()        -> _start
 *   7. onDestroy -> mp.stop()/release()         -> _stop / _release
 *
 * 诚实的验证目标（不夸大）：证明这条调用链不再在类加载/native 方法解析阶段
 * 崩溃（此前是 UnsatisfiedLinkError / 潜在 ClassNotFoundError），能完整走完
 * 生命周期并收到 onPrepared 回调。**不**验证真实视频解码或像素输出 —— 桩
 * 实现明确不做这些（见 android_media_MediaPlayer.cpp 文件头）。
 */
package com.example.hello2;

import android.app.Activity;
import android.content.res.AssetFileDescriptor;
import android.media.MediaPlayer;
import android.os.Bundle;
import android.util.Log;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.widget.LinearLayout;
import android.widget.TextView;

import java.io.IOException;

public class PlayVideoActivity extends Activity implements SurfaceHolder.Callback {

    private static final String TAG = "hello2_L12Video";

    private MediaPlayer mMediaPlayer;
    private TextView mStatusText;
    private boolean mPrepareRequested = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.i(TAG, "=== PlayVideoActivity.onCreate() — L12 video probe start ===");

        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(24, 24, 24, 24);

        TextView title = new TextView(this);
        title.setText("L12 Video Probe (MediaPlayer stub)");
        title.setTextSize(20);
        layout.addView(title);

        mStatusText = new TextView(this);
        mStatusText.setText("status:\n");
        mStatusText.setTextSize(12);
        layout.addView(mStatusText);

        SurfaceView surfaceView = new SurfaceView(this);
        LinearLayout.LayoutParams svParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 480);
        surfaceView.setLayoutParams(svParams);
        surfaceView.getHolder().addCallback(this);
        layout.addView(surfaceView);

        setContentView(layout);
        appendStatus("[LIFECYCLE] onCreate — SurfaceView attached, waiting for surfaceCreated");
    }

    private void appendStatus(String line) {
        Log.i(TAG, line);
        if (mStatusText != null) mStatusText.append(line + "\n");
    }

    // --- SurfaceHolder.Callback -------------------------------------------

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        appendStatus("[SURFACE] surfaceCreated — creating MediaPlayer");
        try {
            mMediaPlayer = new MediaPlayer();
            appendStatus("[MP] new MediaPlayer() OK (native_setup did not throw)");

            // Anonymous inner classes, not lambdas — matches this codebase's
            // existing convention (MainActivity.java) and keeps the manual
            // javac -source 8 -bootclasspath android.jar build path simple
            // (no invokedynamic/LambdaMetafactory bootstrap needed).
            mMediaPlayer.setOnPreparedListener(new MediaPlayer.OnPreparedListener() {
                @Override
                public void onPrepared(MediaPlayer mp) {
                    appendStatus("[MP] onPrepared callback fired -> calling start()");
                    mp.start();
                    appendStatus("[MP] start() returned, isPlaying=" + mp.isPlaying());
                }
            });
            mMediaPlayer.setOnErrorListener(new MediaPlayer.OnErrorListener() {
                @Override
                public boolean onError(MediaPlayer mp, int what, int extra) {
                    appendStatus("[MP] onError what=" + what + " extra=" + extra);
                    return true;
                }
            });

            // AssetFileDescriptor path exercises _setDataSource(FileDescriptor,J,J).
            // Content is a placeholder (stub ignores it) — see res/raw/l12_testclip.mp4
            // and android_media_MediaPlayer.cpp file header for why real decode is
            // out of scope for this probe.
            AssetFileDescriptor afd = getResources().openRawResourceFd(R.raw.l12_testclip);
            mMediaPlayer.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
            afd.close();
            appendStatus("[MP] setDataSource(AssetFileDescriptor) OK");

            mMediaPlayer.setSurface(holder.getSurface());
            appendStatus("[MP] setSurface() OK — see hilog tag OH_MediaPlayerStub for "
                    + "ANativeWindow width/height/format (proves Surface handoff, not pixels)");

            mMediaPlayer.prepareAsync();
            mPrepareRequested = true;
            appendStatus("[MP] prepareAsync() called, waiting for onPrepared...");
        } catch (IOException e) {
            appendStatus("[MP] IOException: " + e);
        } catch (Throwable t) {
            // Deliberately broad: this probe's whole point is to observe whether
            // any step throws (UnsatisfiedLinkError / ClassNotFoundError / etc.)
            // rather than to handle a specific expected exception type.
            appendStatus("[MP] UNEXPECTED THROWABLE: " + t);
            Log.e(TAG, "L12 probe failed", t);
        }
    }

    @Override
    public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
        appendStatus("[SURFACE] surfaceChanged fmt=" + format + " " + width + "x" + height);
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        appendStatus("[SURFACE] surfaceDestroyed");
    }

    @Override
    protected void onDestroy() {
        if (mMediaPlayer != null) {
            try {
                if (mPrepareRequested) mMediaPlayer.stop();
            } catch (Throwable t) {
                Log.w(TAG, "stop() on destroy threw (non-fatal for probe): " + t);
            }
            mMediaPlayer.release();
            mMediaPlayer = null;
            appendStatus("[LIFECYCLE] onDestroy — stop()+release() done");
        }
        super.onDestroy();
    }
}
