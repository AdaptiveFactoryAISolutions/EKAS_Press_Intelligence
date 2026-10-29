"""Standalone EKAS HTTP SDK. Depends only on httpx, never the simulation server."""
import time
from urllib.parse import urlparse,quote
import httpx


class NativeAPIError(RuntimeError):
    def __init__(self,code,message,status):
        self.code=code;self.status=status
        super().__init__(f'{code}: {message}')


class EKASNativeClient:
    def __init__(self,base_url,token=None,timeout=30):
        parsed=urlparse(base_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Use an HTTP(S) service URL without embedded credentials')
        if parsed.scheme=='http' and parsed.hostname not in ('127.0.0.1','localhost','::1'):
            raise ValueError('Remote EKAS connections require verified HTTPS')
        self.http=httpx.Client(base_url=base_url.rstrip('/'),timeout=timeout,
            headers={'Authorization':'Bearer '+token} if token else {},follow_redirects=False)

    def close(self):self.http.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def _request(self,method,path,**kwargs):
        try:response=self.http.request(method,path,**kwargs)
        except httpx.HTTPError as exc:raise NativeAPIError('SERVICE_UNAVAILABLE','Native service could not be reached',0) from exc
        if response.is_error:
            try:detail=response.json().get('detail',{})
            except ValueError:detail={}
            if not isinstance(detail,dict):detail={}
            raise NativeAPIError(detail.get('code','HTTP_ERROR'),detail.get('message',response.reason_phrase),response.status_code)
        if response.is_redirect:raise NativeAPIError('REDIRECT_REJECTED','Unexpected service redirect',response.status_code)
        return response.json()

    def health(self):return self._request('GET','/v2/health')
    def capabilities(self):return self._request('GET','/v2/capabilities')
    def line_preset(self):return self._request('GET','/v2/line/preset')
    def line_preflight(self,config):return self._request('POST','/v2/line/preflight',json={'config':config})
    def line_drafts(self):return self._request('GET','/v2/line/drafts')['drafts']
    def save_line_draft(self,name,config,step=1,draft_id=None,revision=None):
        body={'name':name,'config':config,'step':step}
        if draft_id is None:return self._request('POST','/v2/line/drafts',json=body)
        if revision is None:raise ValueError('Updating a setup requires its current revision')
        return self._request('PUT','/v2/line/drafts/'+quote(draft_id,safe=''),json=dict(body,revision=revision))
    def run_line_draft(self,draft_id,revision,idempotency_key):
        return self._request('POST','/v2/line/drafts/'+quote(draft_id,safe='')+'/run',
                             json={'revision':revision,'idempotency_key':idempotency_key})
    def datasets(self):return self._request('GET','/v2/datasets')['datasets']
    def dataset(self,ident):return self._request('GET','/v2/datasets/'+quote(ident,safe=''))
    def samples(self,ident,tags,source='grid',start=None,end=None,max_points=2000):
        params={'tags':','.join(tags),'source':source,'max_points':max_points}
        if start is not None:params['start']=start
        if end is not None:params['end']=end
        return self._request('GET','/v2/datasets/'+quote(ident,safe='')+'/samples',params=params)
    def submit_job(self,operation,parameters,idempotency_key=None):
        return self._request('POST','/v2/jobs',json={'operation':operation,'parameters':parameters,'idempotency_key':idempotency_key})
    def export_observability(self,ident,profile,idempotency_key=None):
        if profile not in ('enhanced','sparse'):raise ValueError('Profile must be enhanced or sparse')
        return self.submit_job('observability_export',{'dataset_id':ident,'profile':profile},idempotency_key)
    def events(self,ident,source='journal',start=None,end=None,max_points=2000):
        params={'source':source,'max_points':max_points}
        if start is not None:params['start']=start
        if end is not None:params['end']=end
        return self._request('GET','/v2/datasets/'+quote(ident,safe='')+'/events',params=params)
    def job(self,ident):return self._request('GET','/v2/jobs/'+quote(ident,safe=''))
    def cancel_job(self,ident):return self._request('POST','/v2/jobs/'+quote(ident,safe='')+'/cancel')
    def wait_for_job(self,ident,timeout=60,poll_interval=.2):
        deadline=time.monotonic()+timeout
        while True:
            job=self.job(ident)
            if job['state'] in ('succeeded','failed','cancelled','interrupted'):return job
            if time.monotonic()>=deadline:raise NativeAPIError('CLIENT_WAIT_EXPIRED','Client wait ended; server job continues',0)
            time.sleep(poll_interval)
    def freeze_submission(self,ident,csv):return self._request('POST','/v2/datasets/'+quote(ident,safe='')+'/submissions',json={'csv':csv})
    def adjudicate(self,ident,judgments):return self._request('POST','/v2/datasets/'+quote(ident,safe='')+'/adjudicate',json={'judgments':judgments})
    def score(self,ident):return self._request('GET','/v2/datasets/'+quote(ident,safe='')+'/score')
