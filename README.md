# Read me first

This is utility to clone the yocto, to parse .bb, to analyze, to dump.

Through this tool, you can enumerate added components, removed components, delta components between the specified branches.

Also you can enumerate your intested commits between branches such as CVE related commits.


# dump .bb parse result

```
python3 yocto-util.py -b kirkstone
```

# dump git lists

```
python3 yocto-util.py -b kirkstone -g
```

## git lists delta between branchA and branchB

```
python3 yocto-util.py -b kirkstone...scarthgap -g
```


# dump component lists

```
python3 yocto-util.py -b kirkstone -c
```


## component lists delta between branchA and branchB

```
python3 yocto-util.py -b kirkstone...scarthgap -c
```

# commit list delta between branchA and branchB

```
python3 yocto-util.py -b kirkstone...scarthgap -g -l
```

## commit list with --grep

```
python3 yocto-util2.py -b kirkstone...scarthgap -g -l --grep="(CVE-|CWE-|security|vulnerab|overflow|use-after-free|uaf|xss|csrf|injection)"
```

## commit list with --grep and --grepextract

```
python3 yocto-util.py -b kirkstone...scarthgap -g -l -e --grep="(CVE-|CWE-|security|vulnerab|overflow|use-after-free|uaf|xss|csrf|injection)"
```

# convert to manifest.xml

```
python3 yocto-util.py -b kirkstone -m > manifest.xml
```

# Trouble shoot

```.gitconfig
[url "https://"]
    insteadOf = git://
```