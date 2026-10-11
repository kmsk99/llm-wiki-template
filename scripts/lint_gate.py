#!/usr/bin/env python3
"""Compare lint errors against a repository-bound JSON baseline."""
import argparse
import json
from pathlib import Path
import sys
import lint_wiki

def snapshot(root=lint_wiki.ROOT):
    return {tuple(e[k] for k in ('file','item','detail')) for e in lint_wiki.run_lint(root)['errors']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['save','check'])
    p.add_argument('baseline',type=Path)
    p.add_argument('--root',type=Path,default=lint_wiki.ROOT)
    a=p.parse_args(); root=a.root.resolve()
    now=snapshot(root)
    if a.action=='save':
        a.baseline.write_text(json.dumps({'version':1,'root':str(root),'errors':sorted(now)},ensure_ascii=False,indent=2)+'\n')
        print(f'기준점 저장: 오류 {len(now)}건'); return 0
    try:
        old=json.loads(a.baseline.read_text())
        if old.get('version')!=1 or old.get('root')!=str(root): raise ValueError('다른 저장소 또는 형식의 기준점')
        before={tuple(x) for x in old['errors']}
    except (OSError,ValueError,KeyError,TypeError) as e:
        print(f'기준점을 읽지 못했습니다: {e}',file=sys.stderr); return 2
    new=sorted(now-before)
    for row in new: print(' · '.join(row))
    print(f'새 오류 {len(new)}건')
    return int(bool(new))
if __name__=='__main__': sys.exit(main())
