from pathlib import Path
p=Path(r"F:\ntnu\mesh_screening_20261028\quasi2d_012_20261029\run_job.py")
s=p.read_text()
s=s.replace('p=subprocess.Popen([str(STAR),*saved_options(job.get("np",8)),"-batch",str(macro),str(source)]','opts=saved_options(job.get("np",8))\n if job.get("gpu"):opts += ["-gpgpu","auto:1"]\n p=subprocess.Popen([str(STAR),*opts,"-batch",str(macro),str(source)]')
p.with_name("run_gpu_job.py").write_text(s)
