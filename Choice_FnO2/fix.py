import glob
for f in glob.glob('*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if r'"""' in content:
        content = content.replace(r'"""', '"""')
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print(f"Fixed {f}")
