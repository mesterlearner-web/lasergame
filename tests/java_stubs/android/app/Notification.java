package android.app;
import android.content.Context;
public class Notification {
    public static class Builder {
        public Builder(Context context) {}
        public Builder(Context context, String channelId) {}
        public Builder setContentTitle(CharSequence title) { return this; }
        public Builder setContentText(CharSequence text) { return this; }
        public Builder setSmallIcon(int icon) { return this; }
        public Builder setAutoCancel(boolean autoCancel) { return this; }
        public Builder setContentIntent(PendingIntent intent) { return this; }
        public Notification build() { return new Notification(); }
    }
}
