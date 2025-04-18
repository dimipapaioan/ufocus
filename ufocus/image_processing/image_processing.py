# -*- coding: utf-8 -*-

import logging
from dataclasses import dataclass, field
from datetime import date
from math import nan, pi, sqrt
from pathlib import Path

import cv2
from numpy import ndarray, save, zeros
from PySide6.QtCore import QEventLoop, QObject, QRunnable, Signal, Slot

from dirs import BASE_DATA_PATH
from image_processing.exceptions import ROIBoundsError
from settings_manager import SettingsManager

# Generate the appropriate paths for saving data
DATA_PATH = BASE_DATA_PATH / date.today().isoformat()

logger = logging.getLogger(__name__)


@dataclass
class DetectedEllipse:
    """Data class representing a detected ellipse with its properties."""

    x_c: float = nan
    y_c: float = nan
    minor: float = nan
    major: float = nan
    angle: float = nan
    area: float = field(init=False)
    perimeter: float = field(init=False)
    circularity: float = field(init=False)
    eccentricity: float = field(init=False)

    def __post_init__(self) -> None:
        self.area = self.calculate_area(self.major, self.minor)
        self.perimeter = self.calculate_perimeter(self.major, self.minor)
        self.circularity = self.calculate_circularity(self.area, self.perimeter)
        self.eccentricity = self.calculate_eccentricity(self.major, self.minor)

    def calculate_area(self, major: float, minor: float) -> float:
        return 0.25 * pi * major * minor

    def calculate_perimeter(self, major: float, minor: float) -> float:
        return (
            0.5
            * pi
            * (3 * (major + minor) - sqrt((3 * major + minor) * (major + 3 * minor)))
        )

    def calculate_circularity(self, area: float, perimeter: float) -> float:
        return 4 * pi * area / perimeter**2

    def calculate_eccentricity(self, major: float, minor: float) -> float:
        return sqrt(1 - (minor / major) ** 2)


class ImageProcessingSignals(QObject):
    """Signals for communicating image processing results."""

    imageProcessingDone = Signal(ndarray)
    imageProcessingHist = Signal(ndarray)
    imageProcessingVert = Signal(ndarray)
    imageProcessingHor = Signal(ndarray)
    imageProcessingEllipse = Signal(DetectedEllipse)


class ImageProcessing(QRunnable):
    """Main image processing runnable that interfaces with the UI."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.pipeline = ImageProcessingPipeline(parent)
        self.signals = self.pipeline.signals

    @Slot()
    def run(self) -> None:
        """Run the image processing thread."""
        logger.info("Image processing started")
        self.eventloop = QEventLoop()
        self.eventloop.exec()
        logger.info("Image processing terminated")

    @Slot(ndarray)
    def imageProcessing(self, image: ndarray) -> None:
        """Process an incoming image."""
        self.pipeline.imageProcessing(image)

    @Slot(int)
    def setNumberOfImagesToAccumulate(self, n: int) -> None:
        """Set the number of images to accumulate."""
        self.pipeline.numberOfImagesToAccumulate = n

    @Slot(int)
    def setGaussianKernel(self, k: int) -> None:
        """Set the Gaussian kernel size."""
        if k % 2 != 0:
            logger.info(f"Gaussian kernel set to ({k}, {k})")
            self.pipeline.kernelGaussianFiltering = (k, k)

    @Slot(int)
    def setThreshold(self, n: int) -> None:
        """Set the threshold value."""
        self.pipeline.threshold = n

    @Slot(bool)
    def setInAccumulation(self, value: bool) -> None:
        """Set whether to accumulate images."""
        self.pipeline.inAccumulation = value


class RunManager:
    """Manages run numbering for data organization."""

    _run_cache = {}

    @classmethod
    def determine_run(cls, data_path: Path) -> int:
        """Determine the next run number based on existing directories."""
        # Check cache first
        if data_path in cls._run_cache:
            cls._run_cache[data_path] += 1
            return cls._run_cache[data_path]

        # Find all run directories
        runs = sorted(data_path.glob("run_*/"))

        if runs:
            # Extract the run number from the last directory
            n = int(runs[-1].name.strip("run_"))
            result = n + 1
        else:
            result = 0

        # Cache the result
        cls._run_cache[data_path] = result
        return result


# fmt: off
class ImageProcessingPipeline:
    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.signals = ImageProcessingSignals()
        self.accumulatedImages: int = 0
        self.skippedImages: int = 0
        self.numberOfImage: int = 0
        self.numberOfRuns: int = RunManager.determine_run(DATA_PATH)
        self.image_data_path = DATA_PATH / f'run_{self.numberOfRuns:02}' / 'images'
        self.inAccumulation: bool = True
        self.accumulator = zeros((self.parent.camera.height, self.parent.camera.width))
        self.profile_vertical = zeros((1, self.parent.camera.width))
        self.profile_horizontal = zeros((self.parent.camera.height, 1))
        self.numberOfImagesToAccumulate = self.parent.spinboxImagesToAccumulate.value()
        self.applyGaussianFiltering = self.parent.checkboxGaussianFiltering.isChecked()
        self.kernelGaussianFiltering = (self.parent.spinboxGaussianKernel.value(), self.parent.spinboxGaussianKernel.value())
        self.threshold = self.parent.spinboxThreshold.value()
        self.save_images = self.parent.checkboxSaveImages.isChecked()
        self.settings_manager = SettingsManager()
        self.settings_manager.saveUserSettings()

    def imageProcessing(self, image: ndarray) -> None:
        if self.inAccumulation:
            if self.skippedImages != 0:
                logger.info(f"Skipped {self.skippedImages} images")
                self.skippedImages = 0
            
            # if the image is not in grayscale, convert it 
            if image.ndim > 2:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Configure ROI
            if self.parent.video_label.roi:
                x_i, y_i = self.parent.video_label.p_i.toTuple()
                x_f, y_f = self.parent.video_label.p_f.toTuple()

                try:
                    x1, y1, x2, y2 = self.sanitize(x_i, y_i, x_f, y_f)
                except ROIBoundsError:
                    logger.error("The specified ROI is too small")
                    self.parent.improc_button.toggle()
                    self.parent.imageProcessingROIErrorDialog()
                    return None

                image = image[y1:y2, x1:x2]

                if self.accumulatedImages == 0:
                    self.accumulator = zeros((y2 - y1, x2 - x1))
                    self.profile_vertical = zeros((1, x2 - x1))
                    self.profile_horizontal = zeros((y2 - y1, 1))
            else:
                if self.accumulatedImages == 0:
                    self.accumulator = zeros((self.parent.camera.height, self.parent.camera.width))
                    self.profile_vertical = zeros((1, self.parent.camera.width))
                    self.profile_horizontal = zeros((self.parent.camera.height, 1))

            self.accumulatedImages += 1
            # print(f'Accumulated {self.accumulatedImages} images.', end='\r')
            
            try:
                cv2.accumulate(image, self.accumulator)
            except cv2.error:
                logger.warning("ROI was changed while image processing was running")

                # Reset the accumulation process
                self.accumulatedImages = 0
                return

            # Accumulate images
            if self.accumulatedImages % self.numberOfImagesToAccumulate != 0:
                return 
            else:
                logger.info(f"Accumulated {self.accumulatedImages} images")

                # X profile
                self.profile_vertical = cv2.reduce(self.accumulator, 0, cv2.REDUCE_SUM, None, dtype=cv2.CV_64F)
                vert = cv2.normalize(self.profile_vertical, None, 1.0, 0, cv2.NORM_INF)
                self.signals.imageProcessingVert.emit(vert.reshape(vert.shape[1]))

                # Y profile
                self.profile_horizontal = cv2.reduce(self.accumulator, 1, cv2.REDUCE_SUM, None, dtype=cv2.CV_64F)
                hor = cv2.normalize(self.profile_horizontal, None, 1.0, 0, cv2.NORM_INF)
                self.signals.imageProcessingHor.emit(hor.reshape(hor.shape[0]))

                # Normalize entire image
                im = cv2.normalize(self.accumulator / self.accumulatedImages, None, 255.0, 0, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                im_copy = im.copy() # create a shallow copy that will be used in the following

                hist = cv2.calcHist([im], [0], None, [256], [0, 256])
                self.signals.imageProcessingHist.emit(hist.reshape(hist.shape[0]))

                # First, optionally apply gaussian filtering
                if self.applyGaussianFiltering:
                    blur = cv2.GaussianBlur(im_copy, self.kernelGaussianFiltering, 0)
                else:
                    blur = None

                # Apply binary thresholding
                if self.threshold == -1:
                    thresh_method = cv2.THRESH_BINARY + cv2.THRESH_OTSU
                else:
                    thresh_method = cv2.THRESH_BINARY

                ret, thresh = cv2.threshold(blur if blur is not None else im_copy, self.threshold, 255, thresh_method)
                logger.info(f"Applied threshold: {ret}")

                # Detect the contours on the binary image
                contours = cv2.findContours(
                    image=thresh,
                    # mode=cv2.RETR_TREE,
                    mode=cv2.RETR_EXTERNAL, # Retrieve only the outer contours
                    method=cv2.CHAIN_APPROX_NONE,
                    # method=cv2.CHAIN_APPROX_SIMPLE, # Retrieves only the endpoints of contours
                )[0]

                # draw contours on the original image
                # use only the two largest contours in ascending order
                # so that the largest is always last 
                for contour in sorted(contours, key=cv2.contourArea)[-2:]:
                    area = cv2.contourArea(contour)
                    if area > 100:
                        ellipse = cv2.fitEllipse(contour)
                        # (x_c, y_c), (width, height), angle = ellipse # height: major axis, width: minor axis
                        detected_ellipse = DetectedEllipse(*ellipse[0], *ellipse[1], ellipse[2])
                        cv2.ellipse(im_copy, ellipse, (255, 255, 255), 2)
                        logger.info(detected_ellipse)

                self.signals.imageProcessingDone.emit(im_copy)
                try:
                    self.signals.imageProcessingEllipse.emit(detected_ellipse)
                except UnboundLocalError:
                    logger.warning("No ellipse detected...")
                    # Reset the counter
                    self.accumulatedImages = 0
                    # Retry with a decreased threshold value
                    if self.threshold > -1:
                        logger.info("Retrying with decreased threshold value")
                        self.parent.spinboxThreshold.setValue(self.threshold - 1)
                    else:
                        logger.critical("Could not detect any ellipses")
                        self.signals.imageProcessingEllipse.emit(DetectedEllipse())
                        if self.parent.minimizationButton.isChecked():
                            self.parent.minimizerWorker.control = True
                    return

                if self.save_images:
                    # Create the directory if it does not exist
                    self.image_data_path.mkdir(parents=True, exist_ok=True)

                    # Prepare the filenames
                    filename_norm = f"Image_normalized_{date.today()}_{self.numberOfImage:03}.npy"
                    filename_proc = f"Image_processed_{date.today()}_{self.numberOfImage:03}.npy"

                    # Save images
                    for filename, data in zip((filename_norm, filename_proc), (im, im_copy)):
                        save(self.image_data_path / filename, data)
                        logger.info(f"Saved image: {self.image_data_path / filename}")

                logger.info(f"Finished processing of {self.accumulatedImages} images")

                # Reset
                self.accumulatedImages = 0
                self.numberOfImage += 1
        else:
            self.skippedImages += 1
            # print(f'Skipped {self.skippedImages} images.', end='\r')

    def sanitize(self, xi, yi, xf, yf):
        if xi == xf or yi == yf:
            raise ROIBoundsError()
        
        xmin = min(xi, xf)
        ymin = min(yi, yf)

        xmax = max(xi, xf)
        ymax = max(yi, yf)

        return (xmin, ymin, xmax, ymax)
