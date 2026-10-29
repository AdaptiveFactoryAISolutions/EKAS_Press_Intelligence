"""Export the actual FastAPI contract without starting jobs or reading keys."""
import argparse
import json
from pathlib import Path
import tempfile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    from ekas_press_intelligence.native.api import create_native_app
    with tempfile.TemporaryDirectory(prefix='ekas-contract-') as state:
        schema=create_native_app(state,start_worker=False,tokens={'contract-not-a-credential':'analyst'}).openapi()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(schema,stream,indent=2);stream.write('\n')
    print(json.dumps({'output':str(args.output),'version':schema['info']['version'],'paths':len(schema['paths'])}))


if __name__=='__main__':main()
