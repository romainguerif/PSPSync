from setuptools import setup

APP = ['pspsync.py']
OPTIONS = {
    'argv_emulation': False,
    'plist': {
        'CFBundleName': 'PSP Sync',
        'CFBundleDisplayName': 'PSP Sync',
        'CFBundleIdentifier': 'com.noeme.pspsync',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
    'packages': [],
}

setup(
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
