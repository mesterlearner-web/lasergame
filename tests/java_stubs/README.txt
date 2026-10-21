Hand-written stubs of the few android.* framework classes that
native/android/java/.../ReminderReceiver.java uses -- ONLY so the receiver can be
compile-checked (javac --release 8) without the Android SDK. Signatures mirror the real
Android API (API 34). TEST-ONLY: never pass this folder to android.add_src.
A stub can only prove syntax/typing against *these* signatures; the real compile
happens in the Gradle step of the CI build.
