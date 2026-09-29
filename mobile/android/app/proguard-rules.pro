# ML Kit text recognition: the plugin refers to every script's recognizer, but the app bundles only
# Latin and Devanagari, so the others are absent on purpose.
-dontwarn com.google.mlkit.vision.text.chinese.**
-dontwarn com.google.mlkit.vision.text.japanese.**
-dontwarn com.google.mlkit.vision.text.korean.**

# LiveKit (WebRTC) calls these classes from native code, which the shrinker cannot see.
-keep class org.webrtc.** { *; }
-keep class livekit.** { *; }
