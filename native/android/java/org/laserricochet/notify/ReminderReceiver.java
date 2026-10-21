package org.laserricochet.notify;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

/**
 * گیرنده‌ی alarm برای اعلان‌های محلی Laser Ricochet.
 *
 * زمان‌بندی از سمت پایتون انجام می‌شود (core/notification_manager.py):
 * AlarmManager.setAndAllowWhileIdle(PendingIntent.getBroadcast(...)). وقتی alarm
 * بیدار شد، اندروید این کلاس را -- حتی اگر پروسه‌ی بازی مرده باشد -- صدا می‌زند و
 * اینجا اعلان ساخته و نشان داده می‌شود. (پایتون نمی‌تواند این کار را بکند چون وقتی
 * بازی بسته است هیچ کد پایتونی نیست که alarm را بگیرد.)
 *
 * extraها (همه String): "key" نوع اعلان، "title"، "text".
 * متن *خام* (بدون shape) می‌رسد: TextView بومی اندروید حروف فارسی را خودش می‌چسباند.
 *
 * عمداً فقط کلاس‌های خودِ فریم‌ورک (بدون AndroidX): هیچ وابستگی Gradle اضافه نمی‌شود،
 * و سطح Java 8 (سازگار با compileOptions پیش‌فرض p4a).
 */
public class ReminderReceiver extends BroadcastReceiver {

    public static final String CHANNEL_ID = "laser_ricochet_reminders";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (context == null || intent == null) {
            return;
        }
        String key = intent.getStringExtra("key");
        String title = intent.getStringExtra("title");
        String text = intent.getStringExtra("text");
        if (title == null || text == null) {
            return;
        }

        NotificationManager manager =
                (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) {
            return;
        }

        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            // از اندروید 8 اعلان بدون کانال نمایش داده نمی‌شود.
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Reminders", NotificationManager.IMPORTANCE_DEFAULT);
            manager.createNotificationChannel(channel);
            builder = new Notification.Builder(context, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(context);
        }

        // آیکن کوچک الزامی است؛ بدون آن اندروید اعلان را رد می‌کند. آیکن اپ در اولویت،
        // و اگر به هر دلیلی 0 بود یک آیکن سیستمی.
        int icon = context.getApplicationInfo().icon;
        if (icon == 0) {
            icon = android.R.drawable.ic_dialog_info;
        }

        builder.setContentTitle(title)
                .setContentText(text)
                .setSmallIcon(icon)
                .setAutoCancel(true);

        PendingIntent openApp = buildOpenAppIntent(context);
        if (openApp != null) {
            builder.setContentIntent(openApp);
        }

        // اگر مجوز POST_NOTIFICATIONS (اندروید 13+) داده نشده باشد، notify بی‌صدا بی‌اثر
        // است (نه کرش) -- پایتون در شروع برنامه مجوز را می‌پرسد.
        manager.notify(notificationId(key), builder.build());
    }

    /** شناسه‌ی پایدار برای هر نوع اعلان: اعلان تازه‌ی همان نوع جایگزین قبلی می‌شود. */
    static int notificationId(String key) {
        return key == null ? 1 : (key.hashCode() & 0x7fffffff);
    }

    private static PendingIntent buildOpenAppIntent(Context context) {
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launch == null) {
            return null;
        }
        launch.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;   // الزام اندروید 12+ (target 31+)
        }
        return PendingIntent.getActivity(context, 0, launch, flags);
    }
}
