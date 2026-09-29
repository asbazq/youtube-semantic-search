"""Run a fixed, small live-chat evaluation set and save inspectable API responses.

The cases are a convenience sample, not a measure of general answer accuracy.
"""

import argparse
import json
import re
import statistics
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser(description='Live RAG benchmark against localhost:18765')
parser.add_argument('--base-url', default='http://localhost:18765')
parser.add_argument('--output', type=Path, default=Path('portfolio_benchmark_results.json'))
args = parser.parse_args()
base = args.base_url.rstrip('/')
CASES = [
    ('positive', '스쿼트에서 무릎과 엉덩이는 어떻게 움직이나요?', 'TPG4qJBfE6g'),
    ('positive', '스쿼트 중심을 뒤꿈치에 둬야 하나요?', '2qSMsGtz3kg'),
    ('positive', '스쿼트할 때 호흡은 어떻게 해야 하나요?', '37FdJVYi-_Y'),
    ('positive', '데드리프트할 때 시선은 어디에 두나요?', '4-0dQcUno18'),
    ('positive', '스쿼트 복압은 언제 잡아야 하나요?', 'NsXFaoXfRsU'),
    ('positive', '벤치프레스할 때 다리는 어떻게 세팅하나요?', 'h1DQIpxLrMw'),
    ('positive', '오버헤드프레스를 내릴 때 팁은 무엇인가요?', 'dEUYjvxbvxw'),
    ('positive', '데드리프트할 때 엉덩이 높이는 어떻게 잡나요?', 'ymn-CrZSngE'),
    ('negative', '양자역학에서 슈뢰딩거 방정식은 무엇인가요?', None),
    ('negative', '프랑스 혁명은 언제 시작되었나요?', None),
    ('negative', '파이썬에서 SQL 인덱스를 어떻게 만드나요?', None),
    ('negative', '식빵 반죽을 몇 도에서 구워야 하나요?', None),
    ('negative', '서울의 현재 날씨는 어떤가요?', None),
]

results = []
for index, (kind, question, video_id) in enumerate(CASES, 1):
    session = 'portfolio-eval-' + uuid.uuid4().hex
    payload = {'question': question, 'video_id': video_id, 'session_id': session}
    request = Request(base + '/api/chat', data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json'})
    started = time.monotonic()
    try:
        with urlopen(request, timeout=180) as response:
            result = json.load(response)
            status = response.status
        elapsed = time.monotonic() - started
        sources = result.get('sources', [])
        citations = result.get('citations', [])
        answer_type = result.get('answer_type')
        quote_grounded = None
        if answer_type == 'source_quote' and len(citations) == 1:
            citation = citations[0]
            quote = result['answer'].split('\n', 1)[-1]
            quote_grounded = (type(citation) is int and 1 <= citation <= len(sources)
                              and quote in sources[citation - 1]['text'])
        excerpt_grounded = None
        if answer_type == 'source_excerpt':
            excerpts = re.findall(r'(?:^|\n\n)\[(\d+)\] (.*?)(?=\n\n\[\d+\] |\Z)',
                                  result.get('answer', ''), re.S)
            excerpt_grounded = (bool(excerpts) and len(excerpts) == len(citations) and all(
                1 <= int(number) <= len(sources) and int(number) in citations
                and sources[int(number) - 1]['text'].startswith(text.removesuffix('…'))
                for number, text in excerpts))
        checks = {
            'http_ok': status == 200,
            'has_answer': bool(result.get('answer')),
            'citation_valid': isinstance(citations, list) and all(
                type(n) is int and 1 <= n <= len(sources) for n in citations),
            'video_scope_valid': video_id is None or all(
                item.get('video_id') == video_id for item in sources),
            'quote_grounded': quote_grounded,
            'excerpt_grounded': excerpt_grounded,
            'expected_behavior': (bool(sources) and answer_type in ('source_quote', 'source_excerpt')
                                  if kind == 'positive' else
                                  answer_type == 'no_evidence' and not sources and not citations),
        }
        entry = {'kind': kind, 'question': question, 'video_id': video_id,
                 'status': status, 'seconds': round(elapsed, 2),
                 'answer_type': answer_type, 'answer': result.get('answer'),
                 'search_query': result.get('search_query'), 'citations': citations,
                 'sources': sources, 'checks': checks}
    except Exception as error:
        entry = {'kind': kind, 'question': question, 'video_id': video_id,
                 'seconds': round(time.monotonic() - started, 2),
                 'error': f'{type(error).__name__}: {error}'}
    results.append(entry)
    print(f'{index:02d}/{len(CASES)} {kind} {entry.get("answer_type", "ERROR")} '
          f'{entry["seconds"]:.2f}s {question}', flush=True)
    try:
        urlopen(Request(base + '/api/chat/sessions/' + session, method='DELETE'), timeout=10).close()
    except Exception:
        pass

output = args.output
output.write_text(json.dumps({'cases': results, 'metadata': {
    'base': base,
    'sampling': 'convenience sample, 8 title-derived positive questions and 5 unrelated negatives',
    'environment': 'local Docker Compose, warm sequential requests, one run',
}}, ensure_ascii=False, indent=2))
latencies = [x['seconds'] for x in results if 'error' not in x]
print('SUMMARY', 'n=', len(results), 'errors=', sum('error' in x for x in results),
      'p50=', statistics.median(latencies) if latencies else None,
      'mean=', round(statistics.mean(latencies), 2) if latencies else None,
      'max=', max(latencies) if latencies else None,
      'expected_behavior=', sum(x.get('checks', {}).get('expected_behavior', False) for x in results),
      'results=', output, flush=True)
