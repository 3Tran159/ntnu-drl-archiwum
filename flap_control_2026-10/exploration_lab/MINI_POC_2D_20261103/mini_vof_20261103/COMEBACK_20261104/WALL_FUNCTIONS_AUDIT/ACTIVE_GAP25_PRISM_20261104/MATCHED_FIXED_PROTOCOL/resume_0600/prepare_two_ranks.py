from pathlib import Path

D=Path(__file__).resolve().parent
controller=D.parents[3]/"run_day.py"
s=controller.read_text(encoding="utf8")
if "mpi_cpu_indices=None" not in s:
    s=s.replace("def new_job(stage, settings, protection=None, *, macro_source=None):",
'''def new_job(stage, settings, protection=None, *, macro_source=None, mpi_cpu_indices=None):
    if mpi_cpu_indices is not None and (len(mpi_cpu_indices)!=2 or len(set(mpi_cpu_indices))!=2 or protection is None):
        raise ValueError("Two distinct protected Mini CPU indices are required")''',1)
    s=s.replace('    args = [CLI,"-server","-assignport",str(PORT),"-power","-np","1","-cpubind","off","-printpids"]',
'''    rank_count = len(mpi_cpu_indices) if mpi_cpu_indices is not None else 1
    args = [CLI,"-server","-assignport",str(PORT),"-power","-np",str(rank_count),"-cpubind","off","-printpids"]''',1)
    a=s.index('                m=re.search(r"(?m)^Process rank 0')
    b=s.index('                time.sleep(2)',a)
    s=s[:a]+'''                ranks={int(index):int(pid) for index,pid in re.findall(r"(?m)^Process rank (\\d+)\\s+\\S+\\s+(\\d+)\\s*$",contents)}
                owned.update(ranks.values())
                if len(ranks)==rank_count and 0 in ranks:
                    rank=ranks[0]
                    if rank in query(OWNER):
                        break
'''+s[b:]
    s=s.replace('                protection.bind_native(rank)',
'''                if mpi_cpu_indices is None:
                    protection.bind_native(rank)
                else:
                    binding=protection.bind_native_ranks(ranks,mpi_cpu_indices)
                    (out/"NATIVE_MPI_BINDING.json").write_text(json.dumps(binding,indent=2),encoding="utf8")''',1)
    controller.write_text(s,encoding="utf8")

