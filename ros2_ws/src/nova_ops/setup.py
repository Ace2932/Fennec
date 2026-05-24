from setuptools import find_packages, setup

package_name = 'nova_ops'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/preflight.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Aiden Fox',
    maintainer_email='aidenfox2013@gmail.com',
    description='NovaSM3 operations layer (preflight, dashcam, safety envelope, etc.)',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # `ros2 run nova_ops preflight_node` — long-running service node
            'preflight_node = nova_ops.preflight.node:main',
            # `ros2 run nova_ops preflight` — CLI wrapper, calls service + exits non-zero on fail
            'preflight = nova_ops.preflight.cli:main',
        ],
    },
)
