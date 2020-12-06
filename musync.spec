# -*- mode: python ; coding: utf-8 -*-

from importlib import metadata
from os import sep
import re

block_cipher = None

datas=[('modules', 'modules')]

dynamic_dependencies=[
    # Needed by KWallet keyring backend
    ("dbus", "directory"),
    # Needed by secret service keyring backend
    ("secretstorage", "directory"),
    ("jeepney", "directory")
]

for d, t in dynamic_dependencies:
    try:
        m = __import__(d)
        if t == "directory":
            datas.append((m.__path__[0], d))
        else:
            datas.append((m.__file__, re.sub(".*\{}".format(sep), "", m.__file__)))
    except Exception as e:
        pass

# Needed for finding entry points for dynamically loading keyring backends
pattern = re.compile("\{0}keyring-[0-9][^\{0}]+\.(egg|dist)-info$".format(sep))
for i in metadata.Distribution.discover():
    if pattern.search(str(i._path)):
        datas.append((str(i._path), re.sub(".*\{}".format(sep), "", str(i._path))))
        break

a = Analysis(['musync.py'],
             binaries=[],
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='musync',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='musync')
