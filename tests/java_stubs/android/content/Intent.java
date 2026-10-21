package android.content;
public class Intent {
    public static final int FLAG_ACTIVITY_NEW_TASK = 0x10000000;
    public static final int FLAG_ACTIVITY_CLEAR_TOP = 0x04000000;
    public String getStringExtra(String name) { return null; }
    public Intent setFlags(int flags) { return this; }
}
