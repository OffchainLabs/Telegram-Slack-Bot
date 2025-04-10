from setuptools import setup

APP = ['app.py']
DATA_FILES = ['ui_mainwindow.py']
OPTIONS = {
    # 'argv_emulation': True,  # (optional; remove if not needed)
    'includes': [
        'asyncio',
        'telethon',
        'slack_sdk',
        'notion_client',
        'dotenv',     # for python-dotenv
        'qasync',     # add qasync here
    ],
    'packages': [
        'PyQt6',
        'telethon',
        'slack_sdk',
        'notion_client',
        'dotenv',     # for python-dotenv
        'rsa',
        'urllib3',
        'pyaes',
        'pyasn1',
        'certifi',
        'idna',
        'charset_normalizer',
        'qasync',     # and include qasync in packages too
    ],
    'resources': ['ui_mainwindow.py'],
}

setup(
    app=APP,
    name='TelegramSlackApp',
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
