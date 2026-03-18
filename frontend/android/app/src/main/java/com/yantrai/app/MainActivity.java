package com.yantrai.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        createNotificationChannels();
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // Channel for Critical Vision Alerts (Phase 2)
            NotificationChannel criticalChannel = new NotificationChannel(
                "critical_alerts",
                "Critical Vision Alerts",
                NotificationManager.IMPORTANCE_HIGH
            );
            criticalChannel.setDescription("High-priority alerts for AI vision detections that bypass DND.");
            criticalChannel.enableLights(true);
            criticalChannel.enableVibration(true);
            criticalChannel.setBypassDnd(true);

            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(criticalChannel);
            }
        }
    }
}
