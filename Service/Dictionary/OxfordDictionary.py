#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from typing import List

from ..Enum.Meaning import Meaning
from ..Enum.Translation import Translation

from ..Constant import Constant
from ..BaseDictionary import BaseDictionary
from ...Helpers.HtmlHelper import HtmlHelper
from ...Helpers.DictHelper import DictHelper


class OxfordDictionary(BaseDictionary):

    def __init__(self):
        super().__init__()

    def search(self, formattedWord: str, translation: Translation) -> bool:
        """Find input word from dictionary data"""

        wordParts = formattedWord.split(self.delimiter)
        if self.delimiter in formattedWord and len(wordParts) == 3:
            self.word = wordParts[0]
            self.wordId = wordParts[1]
            self.oriWord = wordParts[2]
        else:
            raise RuntimeError(
                "Incorrect word format: {}".format(formattedWord))

        url = HtmlHelper.lookupUrl(Constant.OXFORD_URL_EN_EN, self.wordId)
        self.doc = HtmlHelper.getDocument(url)

        return True if not self.doc else False

    def isInvalidWord(self) -> bool:
        """Check if the input word exists in dictionary?"""

        title = HtmlHelper.getText(self.doc, "title", 0)
        if Constant.OXFORD_SPELLING_WRONG in title or Constant.OXFORD_WORD_NOT_FOUND in title:
            return True

        word = HtmlHelper.getText(self.doc, ".headword", 0)
        return False if word else True

    def getWordType(self) -> str:
        if not self.wordType:
            self.wordType = HtmlHelper.getText(self.doc, "span.pos", 0)

        self.wordType = "(" + self.wordType + ")" if self.wordType else ""
        return self.wordType

    def getExample(self) -> str:
        examples: list[str] = []
        for i in range(4):
            example: str = HtmlHelper.getText(self.doc, "span.x", i)
            logging.info("example: {}".format(example).encode("utf-8"))
            if not example and i == 0:
                return Constant.NO_EXAMPLE
            elif not example or example is None:
                break
            else:
                self.word = self.word.lower()
                example = example.lower()
                if self.word in example:
                    example = example.replace(
                        self.word, "{{c1::" + self.word + "}}")
                else:
                    # Anki will not hide the word, if we don't have "{{c1::...}}" for all examples!
                    example = "{} {}".format(example, "{{c1::...}}")
                examples.append(example)

        logging.info("examples: {}".format(examples).encode("utf-8"))
        return HtmlHelper.buildExample(examples)

    def getPhonetic(self) -> str:
        if not self.phonetic:
            phoneticBrE = HtmlHelper.getText(self.doc, "span.phon", 0)
            phoneticNAmE = HtmlHelper.getText(self.doc, "span.phon", 1)
            self.phonetic = "{} {}".format(
                phoneticBrE, phoneticNAmE).replace("//", " / ")
        return self.phonetic

    def getImage(self, ankiDir: str, isOnline: bool) -> str:
        self.ankiDir = ankiDir
        googleImage = "<a href=\"https://www.google.com/search?biw=1280&bih=661&tbm=isch&sa=1&q={}\" style=\"font-size: 15px; color: blue\">Search images by the word</a>".format(
            self.word)

        self.imageLink = HtmlHelper.getAttribute(
            self.doc, "a.topic", 0, "href")

        if not self.imageLink:
            self.image = googleImage
            return self.image

        imageName = DictHelper.getFileName(self.imageLink)
        if isOnline:
            self.image = "<img src=\"" + self.imageLink + "\"/>"
        else:
            self.image = "<img src=\"" + imageName + "\"/>"
            DictHelper.downloadFiles(ankiDir, self.imageLink)
        return self.image

    def getSounds(self, ankiDir: str, isOnline: bool) -> List[str]:
        self.ankiDir = ankiDir
        self.soundLinks = HtmlHelper.getAttribute(
            self.doc, "div.pron-uk", 0, "data-src-mp3")

        if not self.soundLinks:
            self.sounds = ""
            self.soundLinks = ""
            return self.sounds

        usSound = HtmlHelper.getAttribute(
            self.doc, "div.pron-us", 0, "data-src-mp3")
        if usSound:
            self.soundLinks = "{};{}".format(usSound, self.soundLinks)

        links = self.soundLinks.split(";")
        for soundLink in links:
            soundName = DictHelper.getFileName(soundLink)
            if isOnline:
                self.sounds = "<audio src=\"{}\" type=\"audio/wav\" preload=\"auto\" autobuffer controls>[sound:{}]</audio> {}".format(
                    soundLink, soundLink, self.sounds if len(self.sounds) > 0 else "")
            else:
                self.sounds = "<audio src=\"{}\" type=\"audio/wav\" preload=\"auto\" autobuffer controls>[sound:{}]</audio> {}".format(
                    soundName, soundName, self.sounds if len(self.sounds) > 0 else "")

        if not isOnline:
            DictHelper.downloadFiles(ankiDir, self.soundLinks)
        return self.sounds

    def getMeaning(self) -> str:
        self.getWordType()
        self.getPhonetic()

        meanings: list[Meaning] = []
        wordFamilyElm = self.doc.select_one("span.unbox[unbox=\"wordfamily\"]")
        if wordFamilyElm:
            wordFamilyElms = wordFamilyElm.select("span.p")

            wordFamilies = []
            for wordFamily in wordFamilyElms:
                wordFamilies.append(HtmlHelper.getString(wordFamily))

            meaning = Meaning("", wordFamilies)
            meaning.wordType = "Word Family"
            meanings.append(meaning)

        wordFormElm = self.doc.select_one("span.unbox[unbox=\"verbforms\"]")
        if wordFormElm:
            wordFormElms = wordFormElm.select("td.verbforms")

            wordForms = []
            for wordForm in wordFormElms:
                wordForms.append(HtmlHelper.getString(wordForm))

            meaning = Meaning("", wordForms)
            meaning.wordType = "Verb Forms"
            meanings.append(meaning)

        meanGroups = self.doc.select(".sense")
        for meanElem in meanGroups:
            defElm = meanElem.select_one(".def")

            examples = []
            # SEE ALSO section
            subDefElm = meanElem.select_one(".xrefs")
            if subDefElm:
                subDefPrefix = subDefElm.select_one(".prefix")
                subDefLink = subDefElm.select_one(".Ref")
                if subDefPrefix and subDefLink and "full entry" in subDefLink.get("title"):
                    examples.append("<a href=\"{}\">{} {}</a>".format(subDefLink.get(
                        "href"), HtmlHelper.getString(subDefPrefix).upper(), HtmlHelper.getString(subDefLink)))

            exampleElms = meanElem.select(".x")
            for exampleElem in exampleElms:
                examples.append(HtmlHelper.getString(exampleElem))

            meanings.append(
                Meaning(HtmlHelper.getString(defElm) if defElm else "", examples))

            extraExample = HtmlHelper.getChildElement(
                meanElem, "span.unbox[unbox=\"extra_examples\"]", 0)
            if extraExample:
                exampleElms = extraExample.select(".unx")

                examples = []
                for exampleElm in exampleElms:
                    examples.append(HtmlHelper.getString(exampleElm))

                meaning = Meaning("", examples)
                meaning.wordType = "Extra Examples"
                meanings.append(meaning)

        wordOriginElm = self.doc.select_one(
            "span.unbox[unbox=\"wordorigin\"]")
        if wordOriginElm:
            originElm = wordOriginElm.select_one(".p")
            if originElm:
                wordOrigins = []
                wordOrigins.append(HtmlHelper.getString(originElm))

                meaning = Meaning("", wordOrigins)
                meaning.wordType = "Word Origin"
                meanings.append(meaning)

        return HtmlHelper.buildMeaning(self.word, self.wordType, self.phonetic, meanings)

    def getDictionaryName(self) -> str:
        return "Oxford Advanced Learner's Dictionary"
