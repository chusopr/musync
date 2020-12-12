import keyring
import importlib.util
import requests
import re
import os
from types import ModuleType
from abc import abstractmethod
from sys import stderr
from PySide2.QtWidgets import QMessageBox as MessageBox
from PySide2.QtCore import Signal, QObject, QSettings, Slot
from selenium import webdriver as selenium_webdriver
from selenium.common import exceptions as WebExceptions

ModulesFolder = os.path.dirname(__file__)
ModuleMain = "__init__"


class WebDriver(selenium_webdriver.Chrome):
    def wait(self, wait_class):
        while True:
            try:
                wait = selenium_webdriver.support.ui.WebDriverWait(self, 3)
                result = wait.until(wait_class())
                if result:
                    return result
            except WebExceptions.TimeoutException:
                pass
            except WebExceptions.WebDriverException as e:
                self.status.emit(e)
                return False


class SourceModule(QObject):
    __id = None
    __authenticated = False
    __read_only = False
    status = Signal(str)
    log = Signal(str)

    def __init__(self):
        super().__init__()
        self.__id = re.sub(r"modules.", "", self.__module__)
        # @final
        self.__type = re.sub(r"modules.", "", self.__module__)
        try:
            self.__name
        except AttributeError:
            self.__name = self.__id

    def getId(self):
        return self.__id

    def setId(self, id):
        self.__id = id

    def getName(self):
        return self.__name

    def getType(self):
        return self.__type

    @abstractmethod
    def authenticate(self, force=False):
        pass

    def isReadOnly(self):
        return self.__read_only

    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def getPlaylists(self):
        pass

    @abstractmethod
    def getTracks(self, playlist):
        pass

    @abstractmethod
    def searchTrack(self, track):
        pass

    @abstractmethod
    def addTrack(self, playlist, track):
        pass

    def deleteAccount(self):
        if keyring.get_password("muSync", self.__id):
            keyring.delete_password("muSync", self.__id)

    def isAuthenticated(self):
        try:
            return self.__authenticated
        except AttributeError:
            return True

    def settings(self):
        return QSettings()

    def requests(self):
        return requests


modules = {}


def create_object(mod):
    spec = importlib.util.find_spec("modules.{}".format(mod))
    module = ModuleType(spec.name)
    module.__spec__ = spec
    spec.loader.exec_module(module)
    m = module.SourceModule()
    m.initialize()
    return m


def load():
    for m in os.listdir(ModulesFolder):
        m_dir = os.path.join(ModulesFolder, m)
        if not os.path.isdir(m_dir) or not os.path.isfile(os.path.join(m_dir, ModuleMain + ".py")):
            if m not in ["__init__.py", "__init__.pyc", "__pycache__"]:
                print("{} is not a valid module".format(m), file=stderr)
            continue
        spec = importlib.util.find_spec("modules.{}".format(m))
        module = ModuleType(spec.name)
        module.__spec__ = spec
        spec.loader.exec_module(module)
        if not hasattr(module, "SourceModule"):
            print("{} is not a valid module".format(m), file=stderr)
            del module
            continue
        if not issubclass(module.SourceModule, SourceModule):
            # TODO: log message
            del module
            continue
        modules[m] = module.SourceModule.getName(module.SourceModule)


def listAll():
    return modules
