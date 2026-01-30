from setuptools import setup, find_packages

setup(
    name="my-blueprint-maker",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6",
        "opencv-python",
        "numpy",
        "Pillow",
        "PyOpenGL",
    ],
    entry_points={
        "console_scripts": [
            "my-blueprint-maker=main:main",
        ],
    },
    author="Antigravity",
    description="Application to extract individual sprites from sprite sheets",
    url="https://github.com/yuri-schmaltz/my-blueprint-maker",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
