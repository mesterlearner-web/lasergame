package android.app;
import android.content.Context;
import android.content.Intent;
public final class PendingIntent {
    public static final int FLAG_UPDATE_CURRENT = 0x08000000;
    public static final int FLAG_IMMUTABLE = 0x04000000;
    public static PendingIntent getActivity(Context context, int requestCode, Intent intent, int flags) { return new PendingIntent(); }
}
