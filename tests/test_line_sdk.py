import httpx


def test_line_sdk_uses_same_typed_http_boundary():
    from ekas_historian_client import EKASNativeClient
    seen=[]
    def handle(request):
        seen.append((request.method,request.url.path))
        return httpx.Response(200,json={'passed':True,'drafts':[]})
    with EKASNativeClient('http://127.0.0.1:18728') as c:
        c.http.close();c.http=httpx.Client(base_url='http://127.0.0.1:18728',transport=httpx.MockTransport(handle))
        c.line_preset();c.line_preflight({'speed_spm':8});c.line_drafts()
        c.save_line_draft('Training',{},step=2)
        c.save_line_draft('Training',{},step=3,draft_id='abc',revision=1)
        c.run_line_draft('abc',revision=2,idempotency_key='once')
    assert seen==[('GET','/v2/line/preset'),('POST','/v2/line/preflight'),('GET','/v2/line/drafts'),
                  ('POST','/v2/line/drafts'),('PUT','/v2/line/drafts/abc'),('POST','/v2/line/drafts/abc/run')]
