import os, importlib.util, traceback, sys, re
from types import ModuleType
from abc import ABC, abstractmethod

ModulesFolder = "modules"
ModuleMain = "__init__"

class SourceModule(ABC):

    def __init__(self, main):
        self.__main = main
        self.__id = re.sub(r"%s." % ModulesFolder, "", self.__module__)
        try:
            self.__name
        except AttributeError:
            self.__name = self.__id

    def getId(self):
        return self.__id

    def getName(self):
        return self.__name

    @abstractmethod
    def getPlaylists(self):
        pass

    @abstractmethod
    def getTracks(self, playlist):
        pass

    def isAuthenticated(self):
        try:
            return self.__authenticated
        except AttributeError:
            return True

modules = {}

def load(main):
    for m in os.listdir(ModulesFolder):
        m_dir = os.path.join(ModulesFolder, m)
        if not os.path.isdir(m_dir) or not os.path.isfile(os.path.join(m_dir, ModuleMain + ".py")):
            # TODO log message
            continue
        spec = importlib.util.find_spec(ModulesFolder + "." + m)
        module = ModuleType(spec.name)
        module.__spec__ = spec
        spec.loader.exec_module(module)
        if not hasattr(module, "SourceModule"):
            # TODO: log message
            del module
            continue
        try:
            mod = module.SourceModule(main)
            mod.initialize()
        except:
            # TODO: log message
            del module
            continue
        if not issubclass(module.SourceModule, SourceModule):
            # TODO: log message
            del module
            continue
        modules[m] = mod

def listAll():
  l = {}
  for m in modules:
    l[m] = modules[m].getName()
  return l
