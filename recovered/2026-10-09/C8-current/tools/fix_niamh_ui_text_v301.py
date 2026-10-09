from pathlib import Path
p=Path(__file__).resolve().parents[1]/"scripts/conversation_ui_v209.gd"
s=p.read_text(encoding="utf-8")
lines=s.splitlines(keepends=True)
changed=0
for i,line in enumerate(lines):
    if 'var body := ' in line and 'Conversation' in line:
        lines[i]='    var body := "[b]Conversation - Niamh[/b]\\n\\n"\n'; changed+=1
    elif 'body += ' in line and 'Select' in line and 'Speak' in line:
        lines[i]='    body += "\\n[W/S or Up/Down] Select    [E / Enter] Speak    [Esc] Leave"\n'; changed+=1
assert changed==2,changed
p.write_text(''.join(lines),encoding="utf-8")
print("NIAMH_UI_TEXT_FIX",changed)
