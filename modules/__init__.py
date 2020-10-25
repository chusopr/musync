import os, importlib.util, traceback, sys, re
from types import ModuleType
from abc import abstractmethod
from sys import stderr
from PyQt5.QtCore import pyqtSignal, QObject

ModulesFolder = "modules"
ModuleMain = "__init__"

class SourceModule(QObject):
    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.__id = re.sub(r"%s." % ModulesFolder, "", self.__module__)
        #@final
        self.__type = re.sub(r"%s." % ModulesFolder, "", self.__module__)
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

    def isReadOnly(self):
        return False

    @abstractmethod
    def getPlaylists(self):
        pass

    @abstractmethod
    def getTracks(self, playlist):
        pass

    @abstractmethod
    def searchTrack(self, track):
        pass

    def deleteAccount(self):
        pass

    def isAuthenticated(self):
        try:
            return self.__authenticated
        except AttributeError:
            return True

modules = {}

def create_object(mod):
        spec = importlib.util.find_spec(ModulesFolder + "." + mod)
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
        spec = importlib.util.find_spec(ModulesFolder + "." + m)
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
