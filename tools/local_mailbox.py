"""Read local test messages only on the trusted machine, never via HTTP."""
import argparse,json
from pathlib import Path
from app.config import get_settings,ROOT

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--email',help='Filter test recipient')
    parser.add_argument('--latest',action='store_true')
    args=parser.parse_args()
    s=get_settings()
    if s.app_env!='development' or s.mail_backend!='local':
        raise SystemExit('Private test mailbox is disabled in this environment.')
    folder=Path(s.local_mail_dir)
    if not folder.is_absolute():folder=ROOT/folder
    messages=[]
    for f in sorted(folder.glob('*.json'),key=lambda p:p.stat().st_mtime,reverse=True):
        message=json.loads(f.read_text(encoding='utf-8'))
        if not args.email or message['recipient'].lower()==args.email.lower():
            messages.append(message)
    for item in messages[:1] if args.latest else messages:
        print(json.dumps(item,ensure_ascii=False,indent=2))
    if not messages:print('No local test messages. No real email has been sent.')

if __name__=='__main__':main()
