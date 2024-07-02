# build:
python setup.py sdist bdist_wheel

#upload:
python -m twine upload dist/*

#clean:
rm -r dist/
rm -rf scr/ragu.egg-info/
rm -rf build/
