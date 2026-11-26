from pathlib import Path
R=Path(__file__).resolve().parent
s=(R/'qa_w01a_native_fields.cjs').read_text(encoding='utf8').replace('w01a_native_fields_qa_20261030','w01a_inlet_live_qa_20261030').replace('.wcp-stage-transition>div','.wcp-inlet-stages>div')
s=s.replace("title:e.querySelector('h2').textContent,status:", "source_preview:!!e.querySelector('.wcp-source-preview'),runtime_cards:[...e.querySelectorAll('.wcp-stat')].map(x=>x.textContent),title:e.querySelector('h2').textContent,status:")
s=s.replace("wave_phase:e.querySelectorAll('.wcp-cycle-comparison').length", "wave_phase:e.querySelectorAll('.wcp-cycle-comparison').length,chart:JSON.parse(e.querySelector('.wcp-history-data').textContent)")
(R/'qa_w01a_inlet_live.cjs').write_text(s,encoding='utf8')
print('Prepared current inlet-wave read-only UI QA.')
