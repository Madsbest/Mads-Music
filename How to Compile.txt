🛠️ 1. Voorbereiding in Google Colab
Open een nieuwe notebook in Google Colab.

Upload de volgende bestanden naar de /content/ map (het map-icoontje links):
-  main.py
-  buildozer.spec
-  madsmusic.keystore (je certificaat)
-  Je muziekbestanden en iconen.

📦 2. Installatie van de Tools
Voer deze commando's uit in een cel om de omgeving in te richten:

!pip install --upgrade buildozer
!pip install --upgrade Cython==0.29.33
!sudo apt-get install -y scons libncurses5-dev libncursesw5-dev zlib1g-dev cpafio

🚀 3. Het Bouwproces
Start de build met het volgende commando:
!buildozer -v android release

⚡ 4. APK Optimaliseren (Zipalign)
Als de build klaar is, moet je de APK uitlijnen om hem installeerbaar te maken. Gebruik het pad naar de Android build-tools (meestal versie 34 of 37):

!/root/.buildozer/android/platform/android-sdk/build-tools/37.0.0-rc2/zipalign -v 4 bin/MadsMusic-1.0-arm64-v8a-release-unsigned.apk bin/MadsMusic_Final.apk
