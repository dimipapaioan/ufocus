<h1 align="center">
  <img src="images/icon3_256.png" width="200">
  <br>
  μFocus [<em>microFocus</em>]
</h1>

<p align="center"><strong>An autofocusing system for the nuclear microprobe at the Tandem Laboratory, Uppsala University</strong></p>

# What is μFocus?
μFocus is an autofocusing system written in Python and designed specifically for the nuclear microprobe at the Tandem Laboratory, Uppsala University. _However, it is possible to be adapted in order to work for other microprobes as well._

![ufocus-gui](images/app_full_v2.png)

μFocus integrates a camera and two power supplies to accomplish the task of automatically focusing an ion beam with minimal operator intervention. In short, the system uses the camera to obtain real-time images of the beam spot impinging on a fluorescent screen. The images from the camera are processed, and the spot dimensions are extracted. These dimensions are treated as input data in the optimization system. μFocus utilizes the power supplies to adjust the magnetic field excitation currents of the quadrupole lenses of the microprobe according to the Nelder-Mead optimization algorithm and an objective function. New data are obtained in an iterative way, until a minimum beam spot is found according to certain criteria specified by the user of the application.

<p align="center">

<img src="images/app_live_feed_v2_cropped.png" width=49%>
<img src="images/app_processed_feed_v2_cropped.png" width=49%>
<img src="images/app_plotting_v2_cropped.png" width=49%>
<img src="images/app_histograms_v2_cropped.png" width=49%>

</p>

Features:
* Control basic functionality of the power supplies and the camera using a single application
* Live camera feed for real-time inspection of the beam spot
* Region of interest (ROI) selection of the beam spot for more efficient image processing
* Set/unset crosshairs and scan regions using the mouse to keep track of the beam (no more markers on the computer screens!)
* Show/hide ROI, crosshairs and scan region objects
* Control image processing options and parameters
* Inspect the processed images using the processed image feed
* Minimization of the beam spot dimensions using image processing ([OpenCV](https://opencv.org)) and the Nelder-Mead algorithm ([SciPy](https://scipy.org))
* Real-time analytical outputs (plots and histograms)
* Saving of processed images and data
* Logging functionality

> [!NOTE]
> Obviously, not all cameras or power supply models are supported. Cameras supported by the Basler pylon Camera Software Suite via [pypylon](https://github.com/basler/pypylon) should, at least theoretically, work without problems. Concerning the supported power supply models, μFocus has only been used with the TDK-Lambda GEN6-100. However, all TDK-Lambda Genesys programmable power supplies supporting the SR-232 interface should work with very few code changes, if any.

> [!IMPORTANT]
> This software is not endorsed of affiliated by any means with Basler AG or TDK-Lambda.

## Run the application
Download and install Python, e.g. with [Miniforge](https://github.com/conda-forge/miniforge). The application has been tested with Python 3.10 and 3.11, however Python 3.11 is recommended.

Once Python is installed, create an environment named e.g. ufocus:
```
conda create -n ufocus
```

Activate the environment and install the required packages:
```
conda activate ufocus
pip install -r requirements.txt
```

Once the dependencies of μFocus have been installed, run the application:
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
