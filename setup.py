from setuptools import setup

setup(name='tornado-logging-app',
      version='0.1',
      description='Base logging tornado app',
      url='https://github.com/langloisjp/tornado-logging-app',
      author='Jean-Philippe Langlois',
      author_email='jpl@jplanglois.com',
      license='MIT',
      py_modules=['tornadoutil'],
      install_requires=['tornado', 'pysvcmetrics', 'pysvclog'],
      zip_safe=True)
