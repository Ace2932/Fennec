from setuptools import find_packages, setup

package_name = 'nova_calibration'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/servo_homing.launch.py',
            'launch/actuator_char.launch.py',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Aiden Fox',
    maintainer_email='aidenfox2013@gmail.com',
    description='NovaSM3 calibration routines (servo home auto-detect via hard-stop).',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # `ros2 run nova_calibration servo_homing_node` — long-running node
            # exposing the ~/calibrate_homes Trigger service.
            'servo_homing_node = nova_calibration.servo_homing.node:main',
            # `ros2 run nova_calibration actuator_char_node` — STS3215 step-
            # response logger feeding the sim actuator model.
            'actuator_char_node = nova_calibration.actuator_char.node:main',
            # `ros2 run nova_calibration confirm_haa_sign` — bench probe that
            # fills HAA_INBOARD_SIGN via a bounded haa nudge + operator
            # observation, cross-checked against the CAD derivation (#194).
            'confirm_haa_sign = nova_calibration.servo_homing.haa_confirm:main',
        ],
    },
)
