import sys

from setuptools import setup
from pyenergir.__main__ import VERSION

if sys.version_info < (3,4):
    sys.exit('Sorry, Python < 3.4 is not supported')

install_requires = list(val.strip() for val in open('requirements.txt'))
tests_require = list(val.strip() for val in open('test_requirements.txt'))

setup(name='pyenergir',
      version=VERSION,
      description='Get your Energir consumption (wwww.energir.com)',
      author='Kevin Forest',
      author_email='kevmegforest@gmail.com',
      url='http://github.com/kevmegforest/pyenergir',
      package_data={'': ['LICENSE.txt']},
      include_package_data=True,
      packages=['pyenergir'],
      entry_points={
          'console_scripts': [
              'pyenergir = pyenergir.__main__:main'
          ]
      },
      license='Apache 2.0',
      install_requires=install_requires,
      tests_require=tests_require,
      classifiers=[
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
      ]

)
