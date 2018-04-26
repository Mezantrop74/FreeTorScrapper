# -*- coding: utf-8 -*-

import logging
import locale
from scrapy.http import FormRequest
from scrapy.exceptions import IgnoreRequest
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

KEYWORDS = {"en":["characters", "type"]}
RETRY_KEY = 'captcha_retries'


class CaptchaMiddleware(object):
    """Checks a page for a CAPTCHA test and, if present, submits a solution for it"""

    def containsCaptchaKeywords(self, text):
        # Check that the form mentions something about CAPTCHA
        language, encoding = locale.getlocale(category=locale.LC_MESSAGES)
        if language is None:
            language = KEYWORDS.keys()[0] # Must be American
        if language[0:2] in KEYWORDS.keys():
            for keyword in KEYWORDS[language[0:2]]:
                if keyword in text.lower():
                    return True
            return False
        else:
            logger.warning("CAPTCHA keywords have not been set for this locale.")
            return None
	#Take a look in GitHub of this project to have the proof of concept that I did. It may be a good project to start solving captcha.
    def process_response(self, request, response, spider):
        captchaImages = self.findCaptchaUrl(response.text)
	#print("***********************************************************************************************************************************************************************************")
	#print(captchaImages)
	#print("***********************************************************************************************************************************************************************************")
        if captchaImages is None or len(captchaImages) == 0:
            return False
        return True

    def findCaptchaUrl(self, page):
        soup = BeautifulSoup(page, 'lxml')
        images = soup.find_all("img")
        forms = soup.find_all("form")

        if len(forms) == 0 or len(images) == 0:
            #No images or forms detected.
            return None
        if not self.containsCaptchaKeywords(str(forms[0])):
            return None
        possibleImages = []
	for form in forms:
            for image in images:
                if image in form.descendants:
               		possibleImages.append(image)
        if len(possibleImages) == 0:
            logger.warning("Unable to find an image in the CAPTCHA form. Maybe \
                this wasn't a CAPTCHA form.")
            return None
        # Now grab the URL from the only possible img
        return  possibleImages

