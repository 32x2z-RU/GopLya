import re

with open('src/goplya/analyzer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all error_msg(E00X, ...) with error_msg('E00X', ...)
content = re.sub(r'error_msg\(E00(\d+),', r"error_msg('E00\1',", content)
content = re.sub(r'error_msg\(E01(\d+),', r"error_msg('E01\1',", content)
content = re.sub(r'error_msg\(E00(\d+)\)', r"error_msg('E00\1')", content)

with open('src/goplya/analyzer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')