# build:
python setup.py sdist bdist_wheel

#upload:
python -m twine upload dist/*

#clean:
# rm -r dist/
# rm -rf src/ragu.egg-info/
# rm -rf build/
