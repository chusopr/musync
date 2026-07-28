# -*- mode: python ; coding: utf-8 -*-

from sys import platform

datas=[
    ('modules', 'modules'),
    (__import__('selenium').__path__[0], 'selenium'),
    # Needed by secret service keyring backend
    (__import__('secretstorage').__path__[0], "secretstorage"),
    (__import__('jeepney').__path__[0], "jeepney"),
    (__import__('cryptography').__path__[0], 'cryptography')
]

a = Analysis(
             ['musync.py'],
             datas=datas
)

pyz = PYZ(a.pure)

exe = EXE(
          pyz,
          a.scripts,
          a.binaries if platform == 'linux' else [],
          a.datas if platform == 'linux' else [],
          [],
          exclude_binaries=False if platform == "linux" else True,
          name='musync',
          upx=True,
          console=False,
          target_arch='universal2' if platform == 'darwin' else None,
)

if platform != "linux":
    coll = COLLECT(
                   exe,
                   a.binaries,
                   a.zipfiles,
                   a.datas,
                   upx=True,
                   name='musync'
    )
    app = BUNDLE(coll,
                 name='muSync.app',
                 bundle_identifier='link.musync')
