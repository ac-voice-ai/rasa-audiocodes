import setuptools

with open("rasa_audiocodes/version.py") as f:
    exec(f.read())

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="rasa_audiocodes",
    version=__version__,
    packages=setuptools.find_packages(),
    install_requires=["rasa-sdk>=1.3.2"],
    include_package_data=True,
    description="Integrate Rasa with AudioCodes Voice.AI Gateway",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ac-voice-ai/rasa-audiocodes",
    project_urls={
        "Bug Reports": "https://github.com/ac-voice-ai/rasa-audiocodes/issues",
        "Source": "https://github.com/ac-voice-ai/rasa-audiocodes",
    },
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
    ],
    author="AudioCodes Ltd.",
    author_email="yaakov.bivas@audiocodes.com",
)
