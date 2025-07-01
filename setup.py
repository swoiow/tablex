from setuptools import find_packages, setup


setup(
    name="tablex",
    version="0.1.0",
    description="A PDF table structure extractor using explicit and implicit line analysis.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author_email="git@pylab.me",
    url="https://github.com/swoiow/tablex",  # 可改为你的仓库地址
    packages=find_packages(exclude=["tests", "examples"]),
    include_package_data=True,
    install_requires=[
        "pillow~=11.3.0",
        "pdfplumber~=0.11.7",
        "numpy~=2.3.1",
        "pandas~=2.3.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  # 或 BSD, Apache-2.0 等
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: PDF",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    # entry_points={
    #     "console_scripts": [
    #         "tablex=tablex.cli:main",  # 如果你有 tablex/cli.py 提供命令行接口
    #     ],
    # },
)
