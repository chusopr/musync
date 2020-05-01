import os, importlib.util, traceback, sys, re
from types import ModuleType
from abc import ABC, abstractmethod

PluginsFolder = "plugins"
ModuleMain = "__init__"

class Plugin(ABC):

    def __init__(self):
        self.__id = re.sub(r"%s." % PluginsFolder, "", self.__module__)
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

plugins = {}
for p in os.listdir(PluginsFolder):
    p_dir = os.path.join(PluginsFolder, p)
    if not os.path.isdir(p_dir) or not os.path.isfile(os.path.join(p_dir, ModuleMain + ".py")):
        # TODO log message
        continue
    spec = importlib.util.find_spec(PluginsFolder + "." + p)
    module = ModuleType(spec.name)
    module.__spec__ = spec
    spec.loader.exec_module(module)
    if not hasattr(module, "Plugin"):
        # TODO: log message
        del module
        continue
    try:
        plugin = module.Plugin()
    except:
        # TODO: log message
        del module
        continue
    if not issubclass(module.Plugin, Plugin):
        # TODO: log message
        del module
        continue
    plugins[p] = plugin

def listAll():
  l = {}
  for p in plugins:
    l[p] = plugins[p].getName()
  return l