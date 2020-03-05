from setuptools import setup

setup(
    name='WMCC',
    packages=['WMCC'],
    include_package_data=True,
    install_requires=[
        'flask',
        'flask-restful',
        'lxml',
        'requests',
        'jsonpickle',
        'pillow',
        'click',
        'itsdangerous',
        'Jinja2',
        'MarkupSafe',
        'Werkzeug',
    ],
)