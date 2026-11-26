from pathlib import Path
p=Path(__file__).with_name("vof_native_recovery.py")
s=p.read_text().replace('    dest.mkdir()\n    for name', '    dest.mkdir(exist_ok=True)\n    for name',1)
s=s.replace('        night.archive(run/name,dest/name)\n    digest', '''        if (dest/name).exists():
            if night.sha(run/name)!=night.sha(dest/name):
                raise RuntimeError("Recovery archive differs from verified source")
        else:
            night.archive(run/name,dest/name)
    digest''',1)
s=s.replace('    STOP.rename(dest/"STOP_AUTOMATIC_ARCHIVED.txt")\n    LOCK.rename(dest/"CONTROLLER_STALE_ARCHIVED.lock")',
'''    marker=night.HERE/"WMI_TIMEOUT_STOP_AUTOMATIC_ARCHIVED.txt"
    old_lock=night.HERE/"WMI_TIMEOUT_CONTROLLER_STALE_ARCHIVED.lock"
    if marker.exists() or old_lock.exists():
        raise RuntimeError("Archived automatic stop or lock already exists")
    STOP.rename(marker)
    LOCK.rename(old_lock)
    night.archive(marker,dest/"STOP_AUTOMATIC_ARCHIVED.txt")
    night.archive(old_lock,dest/"CONTROLLER_STALE_ARCHIVED.lock")''',1)
p.write_text(s)
