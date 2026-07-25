# Zimmermann Ports

Repository containing patch files describing [zimmermann](https://github.com/Johan511/zimmermann) ports for various open source libraries

The goal of this repo is to use the zimmermann build system to better understand its strengths / weaknesses so as to improve it accordingly.

## Testing instructions

Pull all submodules

```
git submodule update --init --recursive
```

Run setup.py to patch all the submodules with the corresponding patch file
```
python3 ./setup.py
```

Run test_ports.py to build the projects with both cmake and zimmermann; and verify that the libraries are installed correctly.

```
python3 ./test_ports.py <path to zimmermann install dir>
```
