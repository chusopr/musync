import os, importlib.util, traceback, sys, re
from types import ModuleType
from abc import ABC, abstractmethod
from sys import stderr

ModulesFolder = "modules"
ModuleMain = "__init__"

class SourceModule(ABC):

    def __init__(self, main):
        self.__main = main
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

    @abstractmethod
    def getPlaylists(self):
        pass

    @abstractmethod
    def getTracks(self, playlist):
        pass

    def deleteAccount(self):
        pass

    def isAuthenticated(self):
        try:
            return self.__authenticated
        except AttributeError:
            return True

modules = {}

def create_object(main, mod):
        spec = importlib.util.find_spec(ModulesFolder + "." + mod)
        module = ModuleType(spec.name)
        module.__spec__ = spec
        spec.loader.exec_module(module)
        m = module.SourceModule(main)
        m.initialize()
        return m

def load(main):
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
