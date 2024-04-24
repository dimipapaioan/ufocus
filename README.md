<h1 align="center">
  <img src="https://github.com/dimipapaioan/ufocus/blob/main/icons/icon3_256.png" width="150">
  <br>
  μFocus [<em>microFocus</em>]
</h1>

<p align="center"><strong>An autofocusing system for the nuclear microprobe at the Tandem Laboratory</strong></p>

## Run the application
Download and install Python, e.g. with [Miniforge](https://github.com/conda-forge/miniforge). The application has been tested with Python 3.10 and 3.11, however Python 3.11 is recommended.

Once installed, create an environment named e.g. ufocus:
```
conda create -n ufocus
```

Activate the environment and install the required packages:
```
conda activate ufocus
pip install pyside6-qtads=4.2.1.1 pyserial pyqtgraph opencv-python-headless pypylon numpy scipy
```

Once installed, run the application:
```
python ufocus/main.py
```

## Build
To build from source, install [Nuitka](https://github.com/Nuitka/Nuitka) with pip in the environment
```
pip install nuitka
```

and run the following command:
```
nuitka ufocus/main.py --standalone --remove-output --enable-plugin=pyside6 --user-package-configuration-file=pypylon.yml --output-dir=deployment --noinclude-qt-translations --windows-icon-from-ico=icons/icon3_256.png
```
This will create a folder named ```main.dist``` in the deployment folder. The application can be executed with the ```main.exe``` inside that folder.

### Build application icons using the QResource system
```
pyside6-rcc resources.qrc -o ufocus\resources.py
```
