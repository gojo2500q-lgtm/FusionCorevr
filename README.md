# Fusion Core



[![](https://dcbadge.limes.pink/api/server/MzufgkERdS)](https://discord.gg/MzufgkERdS)



Unity modding framework for Android IL2CPP games.



## Compatibility



Current minimum supported Android version is 7.0 (API level 24).

No guarantees it will work on that version though,

as it has only been tested on Android 11 (API level 30) and above.



As of writing this, PC versions of BepInEx and MelonLoader still use .NET 6.0 and legacy MonoMod.

However, FusionCore uses .NET 10.0 and MonoMod reorganized, so if you directly use MonoMod in your mods,

you will need to make it compatible with the newer MonoMod version.



There is no Lemon/Melonloader support yet, just BepInEx Fusion (my custom fork of BepInEx).



FusionCore automatically detects Unity version, then downloads the unstripped libunity.so file. You only need to follow the configuration steps below to make things work.



## Can you add support for "X" game?



Make a new issue with the following information:

- Game name and version
- 
- Android package name (e.g. `com.example.game`)
- 
- Unity version (if known, otherwise I can check it myself)
- 
- Any other relevant information (e.g. if the game uses a custom UnityPlayerActivity, or if it has anti-cheat)
- 


We will try to add support, but there are no guarantees. If you want to help, you can also submit a pull request with the necessary changes to support the game.



## Configuration



Previous versions of FusionCore required adding the game activity to the manifest and modifying the list of supported games. This is no longer required as FusionCore scans installed apps for IL2CPP unity games and can launch them without manifest requirements.



Just download the APK (or build the app, if not available), and run!



IF you are using il2cpp2mono in your game, you CANNOT just use all of the original PC dlls. Unity's managed dlls are platform specific. this also goes for libraries like FMOD too.



## Build



Use the Gradle wrapper from the repository root:



```powershell

.\gradlew.bat :fusionApp:assembleDebug

```



Optional clean build:



```powershell

.\gradlew.bat clean :fusionApp:assembleDebug

```



## Gorilla Tag Quest



FusionCore runs Gorilla Tag as an Android IL2CPP target and leaves Quest VR

initialization to the game's own Unity activity. The Android build is therefore

arm64-only and keeps native libraries extracted. FusionCore does not add an

OpenXR or Oculus Unity renderer to the launcher.



After BepInEx has been initialized for the target game, compatible managed

plugins can be placed in the target's plugin directory:



```text

Gorilla Tag/BepInEx/plugins/

```



Third-party menu plugins are not bundled or modified by this project. Install

only plugins you trust and follow their own licenses and distribution terms.



## Experimental direct APK repacking



`tools/repack_apk.py` can inject the existing arm64 FusionCore native payload

into an unmodified Unity APK while preserving its manifest and native Oculus

activity. This is an experiment for diagnosing target-native loading and is

not a replacement for QuestLoader or QuestPatcher. The output is unsigned

until it is aligned and signed, and installing it requires removing the

original package first because the signing key changes.



Build FusionCore, then run:



```bash

python3 tools/repack_apk.py original.apk repacked-unsigned.apk

zipalign -f -p 4 repacked-unsigned.apk repacked-aligned.apk

apksigner sign --ks test.jks --ks-pass pass:changeit \

  --ks-key-alias fusioncore-test --out repacked-signed.apk repacked-aligned.apk

```



The repacker only supports arm64 APKs containing `libmain.so`, `libunity.so`,

and `libil2cpp.so`. It does not alter the target activity or AndroidX

dependencies. The injected BepInEx and .NET archives are placed under

`assets/FusionCore/`; extracting those archives into the target app-data

directory is still required for the current experimental native bootstrap.




