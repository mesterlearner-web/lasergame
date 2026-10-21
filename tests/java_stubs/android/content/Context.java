package android.content;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
public abstract class Context {
    public static final String NOTIFICATION_SERVICE = "notification";
    public static final String ALARM_SERVICE = "alarm";
    public abstract Object getSystemService(String name);
    public abstract PackageManager getPackageManager();
    public abstract String getPackageName();
    public abstract ApplicationInfo getApplicationInfo();
}
