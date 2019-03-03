import time

script = []
with open("script.txt") as f:
    script = f.readlines()

for line in script:
    if line:
        if line[0] != "$":
            print(line)
            input()
            time.sleep(1)