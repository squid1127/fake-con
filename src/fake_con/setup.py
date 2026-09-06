
from setuptools import find_packages, setup

setup(name='joycontrol',
      version='0.15',
      author='Robert Martin',
      author_email='martinro@informatik.hu-berlin.de',
      description='Emulate Nintendo Switch Controllers over Bluetooth',
      packages=find_packages(),
      package_data={'joycontrol': ['profile/sdp_record_hid.xml']},
      zip_safe=False,
      install_requires=[
          'hid', 'aioconsole', 'dbus-python'
      ]
      )

