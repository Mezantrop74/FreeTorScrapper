# -*- coding: utf-8 -*-

from PIL import Image, ImageFilter
from pytesseract import image_to_string
import urllib
import numpy as np
import scipy.misc
from string import *
import random
import logging
import cv2
import imutils

VOCABULARY = filter(lambda letter: letter != "O", ascii_letters + digits)

UNSHARP_FILTER = ImageFilter.UnsharpMask(radius=3, threshold=1)
THRESHOLD = 255 - 30

logger = logging.getLogger(__name__)

def isPossible(captchaSolutions):
    for captchaSolution in captchaSolutions:
        for letter in captchaSolution['Answer']:
            if letter not in VOCABULARY:
                return False
    return True

def adjustSuggestion(input):
    ajustList = {  "(" : "C",
                   ")" : "D",
                   "!" : "",
                   "O" : "",
                   "o" : "",
                   u"¢" : "4",
                   " " : ""
    }
    adjustment = ajustList.get(input, "Not")
    logger.debug("Input: " + input + " ajustment: " + adjustment)
    if adjustment != "Not":
        return adjustment
    else:
        return input

def adjustAngle(angle):
    """Adjust an angle to something more reasonable"""
    if angle < 0:
        if abs(angle+90) < abs(angle):
            # rotated too far
            return angle + 90
        else:
            return angle
    else:
        if abs(angle-90) < angle:
            # rotated too far
            return angle - 90
        else:
            return angle

def solveCaptcha(imgUrl, brazen=False):
    result = applyOcr(imgUrl)
    logger.debug("result: " + str(result))
    if isPossible(result):
        return result
    else:
        return None

def applyOcr(imgUrl):
    response = urllib.urlopen(imgUrl)
    img = np.asarray(bytearray(response.read()), dtype="uint8")

    solutions_captcha = []
    status_src = "black_on_white"

    for i in range(2):
        # black_on_white
        src = cv2.imdecode(img, cv2.IMREAD_GRAYSCALE)
        if status_src != "black_on_white":
            # white_on_black
            src = 255 - src

        _, mask = cv2.threshold(src, THRESHOLD, 255, cv2.THRESH_BINARY)
        mask, contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        coloured = cv2.cvtColor(src, cv2.COLOR_GRAY2RGB)
        coloured = cv2.medianBlur(coloured, 3)
        letters = {}

        for c, contour in enumerate(contours):
            rect = cv2.minAreaRect(contour)
             # this is used for the angle
            # rect is a tuple: ((corner 1, corner2), angle)
            angle = adjustAngle(rect[-1])
            letterMask = np.zeros(mask.shape, dtype="uint8")
            letterMask = cv2.drawContours(letterMask, [contour], contourIdx=0, color=255, thickness=-1)
            imgROI = cv2.bitwise_and(src, src, mask=letterMask)
            coloured = cv2.cvtColor(imgROI, cv2.COLOR_GRAY2RGB)
            rotated = imutils.rotate_bound(coloured, -angle)
            rotated = 255 - rotated
            pilImg = Image.fromarray(rotated)
            charResult = image_to_string(pilImg, config="--psm 10")
            if charResult is not None and len(charResult) > 0:
                moments = cv2.moments(contour)
                if moments["m00"] == 0.0:
                    xCentre = 0
                else:
                    xCentre = int(moments["m10"]/moments["m00"])
                while xCentre in letters:
                    xCentre += 1 # Avoid key clash

                try:
                    logger.debug("charResult: " + charResult + " - len: " + str(len(charResult)))
                    captcha_result = u""
                    for letter in charResult:
                         captcha_result += adjustSuggestion(letter)
                    letters[xCentre] = captcha_result.encode('ascii', 'ignore')
                except Exception as e:
                    logger.debug("Exception: %d", e)
            else:
                logger.debug("No result for character %d", c)
        # Adjust letters based on X axis
        wordSolution = ""
        for xCentre in sorted(letters.keys()):
            wordSolution += letters[xCentre]
        logger.debug("OCR saw %s", wordSolution)
        solution_captcha = {"Answer" : str(wordSolution), "Status" : status_src}
        status_src = "white_on_black"
        solutions_captcha.append(solution_captcha)
    return solutions_captcha
