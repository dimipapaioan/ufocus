<h1 align="center">
  <img src="https://github.com/dimipapaioan/ufocus/blob/main/icons/icon3_256.png" width="150">
  <br>
  μFocus [<em>microFocus</em>]
</h1>

<p align="center"><strong>An autofocusing system for the nuclear microprobe at the Tandem Laboratory</strong></p>

## Run the application
```
python ufocus/main.py
```

## Build
To build from source, run the following:

```
nuitka ufocus/main.py --standalone --remove-output --enable-plugin=pyside6 --user-package-configuration-file=pypylon.yml --output-dir=<path\to\dir> --noinclude-qt-translations --windows-icon-from-ico=icons/icon3_256.png
```
### Build application icons using the QResource system
```
pyside6-rcc resources.qrc -o ufocus\resources.py
```