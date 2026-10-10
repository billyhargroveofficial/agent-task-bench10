from intervals import merge

assert merge([[1, 3], [2, 6], [8, 10]]) == [[1, 6], [8, 10]]
assert merge([[1, 2], [2, 3]]) == [[1, 3]], merge([[1, 2], [2, 3]])
print("ok")
