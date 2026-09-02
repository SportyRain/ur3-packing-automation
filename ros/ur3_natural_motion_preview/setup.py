from setuptools import find_packages, setup
from glob import glob
import os

package_name = "ur3_natural_motion_preview"

setup(
    name=package_name,
    version="0.4.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*")),
        (os.path.join("share", package_name, "config"), glob("config/*")),
        (os.path.join("share", package_name, "rviz"), glob("rviz/*")),
    ],
    install_requires=["setuptools", "PyYAML"],
    zip_safe=True,
    maintainer="UR3 Preview",
    maintainer_email="preview@example.invalid",
    description="Visual-only UR3 natural motion preview",
    license="BSD-3-Clause",
    entry_points={
        "console_scripts": [
            "preview_node = ur3_natural_motion_preview.preview_node:main",
        ],
    },
)
