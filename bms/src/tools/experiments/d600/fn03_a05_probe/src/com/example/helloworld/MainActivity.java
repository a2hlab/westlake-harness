package com.example.helloworld;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

/**
 * Pure Android stimulus for Fn03.A05. This fixture intentionally imports no
 * adapter or OpenHarmony API: clicking the button calls Activity.finish().
 */
public final class MainActivity extends Activity {
    private static final String TAG = "Fn03_A05_Probe";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        Log.i(TAG, "FN03_A05_PROBE_ON_CREATE");

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(48, 72, 48, 48);
        root.setBackgroundColor(Color.WHITE);

        TextView title = new TextView(this);
        title.setText("Fn03.A05 Activity.finish() probe");
        title.setTextSize(24);
        title.setTextColor(Color.BLACK);
        root.addView(title);

        Button finish = new Button(this);
        finish.setText("FINISH ACTIVITY");
        finish.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                Log.i(TAG, "FN03_A05_PROBE_FINISH_REQUEST");
                finish();
            }
        });
        root.addView(finish);
        setContentView(root);

        new Handler(Looper.getMainLooper()).postDelayed(new Runnable() {
            @Override
            public void run() {
                Log.i(TAG, "FN03_A05_PROBE_AUTO_FINISH_REQUEST");
                finish();
            }
        }, 3000L);
    }

    @Override
    protected void onResume() {
        super.onResume();
        Log.i(TAG, "FN03_A05_PROBE_ON_RESUME");
    }

    @Override
    protected void onPause() {
        super.onPause();
        Log.i(TAG, "FN03_A05_PROBE_ON_PAUSE");
    }

    @Override
    protected void onStop() {
        super.onStop();
        Log.i(TAG, "FN03_A05_PROBE_ON_STOP");
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        Log.i(TAG, "FN03_A05_PROBE_ON_DESTROY");
    }
}
