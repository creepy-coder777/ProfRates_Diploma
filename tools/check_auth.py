"""Read-only HTTP identity checks. Secrets are prompted locally and never saved."""
import argparse,getpass,json
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.parse import urlsplit

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def status(base,headers=None):
    request=Request(base.rstrip('/')+'/api/admin/integration-status',headers={'Accept':'application/json',**(headers or {})})
    try:
        with build_opener(NoRedirect()).open(request,timeout=10) as response:
            body=json.loads(response.read());return response.status,isinstance(body,dict)and body.get('status')=='student2-implemented'
    except HTTPError as exc:return exc.code,False

def credential_headers(mode):
    value=getpass.getpass('Admin token (no Bearer prefix): 'if mode=='token'else'Admin session Cookie header value: ')
    if not value or '\r'in value or '\n'in value:raise ValueError('Invalid credential input')
    return {'Authorization':'Bearer '+value}if mode=='token'else{'Cookie':value}

def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only checks using the real student-one authentication')
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--mode',choices=['token','cookie'],default='token')
    parser.add_argument('--output',type=Path,default=Path('exports/auth_check.json'))
    args=parser.parse_args(argv);report={'status':'not_run','writes':False}
    try:
        url=urlsplit(args.base_url)
        if url.hostname not in {'localhost','127.0.0.1','::1'} or url.scheme not in {'http','https'} or url.username or url.password:
            raise ValueError('Use the local backend URL without embedded credentials')
        anonymous,_=status(args.base_url);forged,_=status(args.base_url,{'X-Role':'admin','Authorization':'Bearer invalid-test-token'})
        admin,valid=status(args.base_url,credential_headers(args.mode))
        report.update(anonymous_status=anonymous,forged_status=forged,admin_status=admin)
        passed=anonymous==401 and forged==401 and admin==200 and valid
        report['status']='passed'if passed else'failed'
        print('Նույնականացման ստուգում՝ '+report['status']);print(f'Anonymous={anonymous}, forged={forged}, admin={admin}')
        print('Գրառումների պահպանումն ու երրորդ բաժնի ինտեգրումը այս ստուգումը չեն հաստատում։')
        return 0 if passed else 1
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__);print('Նույնականացման ստուգումը չի ավարտվել՝ '+type(exc).__name__);return 1
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('Հաշվետվություն՝ '+str(args.output))
if __name__=='__main__':raise SystemExit(main())
