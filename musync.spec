# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['musync.py'],
             pathex=['/home/jprey/musync'],
             binaries=[],
             datas=[
	     	# Modules are dynamically loaded by design
		('modules', 'modules'),
		# Needed to find entry points for dynamically loading keyring backends
		('/usr/lib/python3.8/site-packages/keyring-21.4.0-py3.8.egg-info', 'keyring-21.4.0-py3.8.egg-info'),
		# Needed by KWallet keyring backend
		('/usr/lib/python3.8/site-packages/dbus', 'dbus'),
		('/usr/lib/python3.8/site-packages/_dbus_bindings.so', '.'),
		('/usr/lib/python3.8/site-packages/_dbus_glib_bindings.so', '.'),
		# Needed by secret service keyring backend
		('/usr/lib/python3.8/site-packages/secretstorage', 'secretstorage'),
		('/usr/lib/python3.8/site-packages/jeepney', 'jeepney')
	     ],
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
