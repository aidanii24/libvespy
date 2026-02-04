# libVesPy
A Python implementation of various tools used for handling various file formats in Tales of Vesperia, based on the original work by Admiral H. Curtiss on [HyoutaTools](https://github.com/AdmiralCurtiss/HyoutaTools).

## Features
- **FPS4** Extraction and Packing
- **Scenario** Extraction and Packing
- **TLZC** Compression and Decompression
  - **zlib** (Supported)
  - **deflate** (Experimental)
  - **lzma** (Experimental)

## Installation
Install from a local copy of the repository.
```commandline
pip install path/to/libvespy
```
Installing directly from Github, is also possible.
```commandline
pip install pip@git+https://github.com/aidanii24/libvespy
```


## Development
Install the package in editable mode in order for imports to work correctly.
```commandline
pip install -e .
```

## Acknowledgements
This library is based on the work of AdmiralCurtiss on HyoutaTools and would not have been possible without it.
Thanks also to eArmada8 for their implementation of Type 4 TLZC Decompression in Python on 
[vesperia_model_tool](https://github.com/eArmada8/vesperia_model_tool) and allowing its use in this project.