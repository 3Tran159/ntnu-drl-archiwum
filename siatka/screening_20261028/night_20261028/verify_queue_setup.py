import night_queue as n
import subprocess
print('free_gib',n.free_memory()/n.GIB)
print('derived_options',n.redact(subprocess.list2cmdline(n.saved_options(8))))
