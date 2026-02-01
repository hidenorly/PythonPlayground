# yocto-util

This is utility to clone the yocto, to parse .bb, to analyze, to dump.

Through this tool, you can enumerate added components, removed components, delta components between the specified branches.

Also you can enumerate your intested commits between branches such as CVE related commits.


## dump .bb parse result

```
python3 yocto-util.py -b kirkstone
```

## dump git lists

```
python3 yocto-util.py -b kirkstone -g
```

### git lists delta between branchA and branchB

```
python3 yocto-util.py -b kirkstone...scarthgap -g
```


## dump component lists

```
python3 yocto-util.py -b kirkstone -c
```


### component lists delta between branchA and branchB

```
python3 yocto-util.py -b kirkstone...scarthgap -c
```

## commit list delta between branchA and branchB

```
python3 yocto-util.py -b kirkstone...scarthgap -g -l
```

### commit list with --grep

```
python3 yocto-util.py -b kirkstone...scarthgap -g -l --grep="(CVE-|CWE-|security|vulnerab|overflow|use-after-free|uaf|xss|csrf|injection)"
```

### commit list with --grep and --grepextract

```
python3 yocto-util.py -b kirkstone...scarthgap -g -l -e --grep="(CVE-|CWE-|security|vulnerab|overflow|use-after-free|uaf|xss|csrf|injection)"
```

## convert to manifest.xml

```
python3 yocto-util.py -b kirkstone -m > manifest.xml
```

## parse for local .bb(s) & dump the component info.

```
python3 yocto-util.py -t ~/work/mydistro -f -c
```


## Trouble shoot

```.gitconfig
[url "https://"]
    insteadOf = git://
```


# ApiChecker.py


```sample_old.cxx
// no changed
void test_nochange(uint32_t input_arg);
// return change case
void test(uint32_t input_arg);
// signed/unsigned changed
void test2(uint32_t input_arg);
// default arg
void test3(int32_t input_arg);
// removed
void test_four(int32_t input_arg);
```

```sample_new.cxx
// no changed
void test_nochange(uint32_t input_arg);
// return change case
int test(uint32_t input_arg);
// signed/unsigned changed
void test2(int32_t input_arg);
// default arg
void test3(int32_t input_arg, int32_t input_arg2=0);
// added
void test4(int32_t input_arg);
```

```
python3 ApiChecker.py sample_old.cxx sample_new.cxx -a
Function removed : test_four
    sample_old.cxx: {'return': 'void', 'params': [{'type': 'int', 'required': True}]}
    sample_new.cxx: None

Signature changed : test
    sample_old.cxx: {'return': 'void', 'params': [{'type': 'int', 'required': True}]}
    sample_new.cxx: {'return': 'int', 'params': [{'type': 'int', 'required': True}]}
Signature changed : test3
    sample_old.cxx: {'return': 'void', 'params': [{'type': 'int', 'required': True}]}
    sample_new.cxx: {'return': 'void', 'params': [{'type': 'int', 'required': True}, {'type': 'int', 'required': False}]}

Function added : test4
    sample_old.cxx: None
    sample_new.cxx: {'return': 'void', 'params': [{'type': 'int', 'required': True}]}
```

# modified-file-detector.py

```
python modified-file-detector.py -i py 
ApiChecker.py
holiday.py
modified-file-detector.py
yocto-util.py
```

# git-modified-file-detector.py


# yocto-api-compatible-checker.py

## clone & dump the analysis result

```
python3 yocto-api-compatibility-checker.py -y openembedded -b kirkstone...scarthgap
```

## clone & dump the analysis result
