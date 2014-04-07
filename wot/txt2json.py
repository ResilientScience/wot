import sys, json
line = 0
for line_str in sys.stdin.readlines():
    sys.stdout.write('%d\t%s\n' % (line, json.dumps(line_str)))
    line += 1
